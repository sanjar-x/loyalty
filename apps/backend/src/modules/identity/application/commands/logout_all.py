"""Command handler for logging out all sessions of an identity.

Revokes every active session for the identity and invalidates
permissions cache entries for each revoked session.
"""

import uuid
from dataclasses import dataclass

from src.modules.identity.domain.interfaces import (
    IIdentityRepository,
    ISessionRepository,
)
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.security import IPermissionResolver
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class LogoutAllCommand:
    """Command to revoke all sessions for an identity.

    Attributes:
        identity_id: The identity whose sessions should be revoked.
    """

    identity_id: uuid.UUID


class LogoutAllHandler:
    """Handles bulk session revocation with cache invalidation."""

    def __init__(
        self,
        session_repo: ISessionRepository,
        identity_repo: IIdentityRepository,
        uow: IUnitOfWork,
        permission_resolver: IPermissionResolver,
        logger: ILogger,
    ) -> None:
        self._session_repo = session_repo
        self._identity_repo = identity_repo
        self._uow = uow
        self._permission_resolver = permission_resolver
        self._logger = logger.bind(handler="LogoutAllHandler")

    async def handle(self, command: LogoutAllCommand) -> None:
        """Execute the logout-all command.

        Revokes all active sessions for the identity and invalidates
        the permissions cache for each.

        Args:
            command: The logout-all command.
        """
        async with self._uow:
            revoked_ids = await self._session_repo.revoke_all_for_identity(
                command.identity_id,
            )
            identity = await self._identity_repo.get(command.identity_id)
            if identity:
                identity.bump_token_version()
                await self._identity_repo.update(identity)
            await self._uow.commit()

        # Invalidate permissions cache for all revoked sessions (single round-trip)
        await self._permission_resolver.invalidate_many(revoked_ids)

        self._logger.info(
            "sessions.all_revoked",
            identity_id=str(command.identity_id),
            revoked_count=len(revoked_ids),
        )
