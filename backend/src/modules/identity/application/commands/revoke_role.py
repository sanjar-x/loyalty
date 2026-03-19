"""Command handler for revoking a role from an identity.

Removes the identity-role association, deactivates the role from all
active sessions, and emits a RoleAssignmentChangedEvent for downstream
cache invalidation.
"""

import uuid
from dataclasses import dataclass

from src.modules.identity.domain.events import RoleAssignmentChangedEvent
from src.modules.identity.domain.interfaces import (
    IIdentityRepository,
    IRoleRepository,
    ISessionRepository,
)
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class RevokeRoleCommand:
    """Command to revoke a role from an identity.

    Attributes:
        identity_id: The identity to revoke the role from.
        role_id: The role to revoke.
    """

    identity_id: uuid.UUID
    role_id: uuid.UUID


class RevokeRoleHandler:
    """Handles role revocation with session cleanup and event emission."""

    def __init__(
        self,
        identity_repo: IIdentityRepository,
        role_repo: IRoleRepository,
        session_repo: ISessionRepository,
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
        self._identity_repo = identity_repo
        self._role_repo = role_repo
        self._session_repo = session_repo
        self._uow = uow
        self._logger = logger.bind(handler="RevokeRoleHandler")

    async def handle(self, command: RevokeRoleCommand) -> None:
        """Execute the revoke role command.

        If the identity is not found, this is a no-op. Otherwise, removes the
        role from the identity, deactivates it in all active sessions, and
        emits a domain event.

        Args:
            command: The revoke role command.
        """
        async with self._uow:
            identity = await self._identity_repo.get(command.identity_id)
            if identity is None:
                return

            # Remove from identity_roles
            await self._role_repo.revoke_from_identity(
                identity_id=command.identity_id,
                role_id=command.role_id,
            )

            # Remove from session_roles for active sessions
            active_session_ids = await self._session_repo.get_active_session_ids(
                command.identity_id,
            )
            for sid in active_session_ids:
                await self._session_repo.remove_session_role(sid, command.role_id)

            # Emit RoleAssignmentChangedEvent
            identity.add_domain_event(
                RoleAssignmentChangedEvent(
                    identity_id=command.identity_id,
                    role_id=command.role_id,
                    action="revoked",
                    aggregate_id=str(command.identity_id),
                )
            )
            self._uow.register_aggregate(identity)
            await self._uow.commit()

        self._logger.info(
            "role.revoked",
            identity_id=str(command.identity_id),
            role_id=str(command.role_id),
        )
