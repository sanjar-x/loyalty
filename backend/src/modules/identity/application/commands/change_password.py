"""Command handler for changing an identity's password.

Verifies the current password, hashes the new one outside the transaction,
then updates credentials and revokes all other sessions for security.
"""

import uuid
from dataclasses import dataclass

from src.modules.identity.domain.exceptions import InvalidCredentialsError
from src.modules.identity.domain.interfaces import (
    IIdentityRepository,
    ISessionRepository,
)
from src.shared.exceptions import NotFoundError
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.security import IPasswordHasher, IPermissionResolver
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class ChangePasswordCommand:
    """Command to change an identity's password.

    Attributes:
        identity_id: The identity whose password to change.
        current_session_id: The session making the request (preserved after change).
        current_password: The current password for verification.
        new_password: The new password to set.
    """

    identity_id: uuid.UUID
    current_session_id: uuid.UUID
    current_password: str
    new_password: str


class ChangePasswordHandler:
    """Handles password change with current-password verification and session revocation."""

    def __init__(
        self,
        identity_repo: IIdentityRepository,
        session_repo: ISessionRepository,
        uow: IUnitOfWork,
        hasher: IPasswordHasher,
        permission_resolver: IPermissionResolver,
        logger: ILogger,
    ) -> None:
        self._identity_repo = identity_repo
        self._session_repo = session_repo
        self._uow = uow
        self._hasher = hasher
        self._permission_resolver = permission_resolver
        self._logger = logger.bind(handler="ChangePasswordHandler")

    async def handle(self, command: ChangePasswordCommand) -> None:
        """Execute the change password command.

        Verifies current password, hashes new password outside transaction,
        updates credentials, and revokes all other sessions.

        Args:
            command: The change password command.

        Raises:
            NotFoundError: If the identity has no local credentials.
            InvalidCredentialsError: If the current password is wrong.
        """
        # Hash new password OUTSIDE transaction (CPU-intensive Argon2id)
        new_hash = self._hasher.hash(command.new_password)

        revoked_ids: list[uuid.UUID] = []

        async with self._uow:
            result = await self._identity_repo.get_with_credentials(command.identity_id)
            if result is None:
                raise NotFoundError(
                    message="Identity credentials not found",
                    error_code="CREDENTIALS_NOT_FOUND",
                )

            _identity, credentials = result

            # Verify current password
            if not self._hasher.verify(command.current_password, credentials.password_hash):
                self._logger.warning(
                    "password.change.failed",
                    identity_id=str(command.identity_id),
                    reason="invalid_current_password",
                )
                raise InvalidCredentialsError()

            # Update password hash
            credentials.password_hash = new_hash
            await self._identity_repo.update_credentials(credentials)

            # Revoke all OTHER sessions (keep current session active)
            all_revoked = await self._session_repo.revoke_all_for_identity(
                command.identity_id,
            )
            # Exclude current session from revocation — un-revoke it
            current_session = await self._session_repo.get(command.current_session_id)
            if current_session and current_session.is_revoked:
                current_session.is_revoked = False
                await self._session_repo.update(current_session)
                revoked_ids = [sid for sid in all_revoked if sid != command.current_session_id]
            else:
                revoked_ids = all_revoked

            await self._uow.commit()

        # Invalidate permission cache for revoked sessions
        if revoked_ids:
            await self._permission_resolver.invalidate_many(revoked_ids)

        self._logger.info(
            "password.changed",
            identity_id=str(command.identity_id),
            revoked_sessions=len(revoked_ids),
        )
