"""Command handler for deactivating an identity.

Marks the identity as inactive, revokes all sessions, emits an
IdentityDeactivatedEvent (for GDPR PII cleanup), and invalidates
the permissions cache for all revoked sessions.
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
class DeactivateIdentityCommand:
    """Command to deactivate an identity.

    Attributes:
        identity_id: The identity to deactivate.
        reason: Human-readable deactivation reason.
    """

    identity_id: uuid.UUID
    reason: str = "user_request"


class DeactivateIdentityHandler:
    """Handles identity deactivation with session revocation and cache cleanup."""

    def __init__(
        self,
        identity_repo: IIdentityRepository,
        session_repo: ISessionRepository,
        uow: IUnitOfWork,
        permission_resolver: IPermissionResolver,
        logger: ILogger,
    ) -> None:
        self._identity_repo = identity_repo
        self._session_repo = session_repo
        self._uow = uow
        self._permission_resolver = permission_resolver
        self._logger = logger.bind(handler="DeactivateIdentityHandler")

    async def handle(self, command: DeactivateIdentityCommand) -> None:
        """Execute the deactivate identity command.

        If the identity is not found, this is a no-op. Otherwise, deactivates
        the identity, revokes all active sessions, and invalidates cached
        permissions.

        Args:
            command: The deactivate identity command.
        """
        async with self._uow:
            identity = await self._identity_repo.get(command.identity_id)
            if identity is None:
                return

            # Deactivate identity (emits IdentityDeactivatedEvent)
            identity.deactivate(reason=command.reason)

            # Persist deactivation state (Data Mapper — explicit update required)
            await self._identity_repo.update(identity)

            # Revoke all sessions
            revoked_ids = await self._session_repo.revoke_all_for_identity(
                command.identity_id,
            )

            self._uow.register_aggregate(identity)
            await self._uow.commit()

        # Invalidate permissions cache (outside transaction, single round-trip)
        await self._permission_resolver.invalidate_many(revoked_ids)

        self._logger.info(
            "identity.deactivated",
            identity_id=str(command.identity_id),
            reason=command.reason,
            revoked_sessions=len(revoked_ids),
        )
