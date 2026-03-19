"""Command handler for assigning a role to an identity.

Validates that both identity and role exist, inserts the identity-role
association, propagates the role to all active sessions (NIST compliance),
and emits a RoleAssignmentChangedEvent for cache invalidation.
"""

import uuid
from dataclasses import dataclass

from src.modules.identity.domain.events import RoleAssignmentChangedEvent
from src.modules.identity.domain.exceptions import AccountTypeMismatchError
from src.modules.identity.domain.interfaces import (
    IIdentityRepository,
    IRoleRepository,
    ISessionRepository,
)
from src.shared.exceptions import NotFoundError
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.security import IPermissionResolver
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class AssignRoleCommand:
    """Command to assign a role to an identity.

    Attributes:
        identity_id: The target identity's UUID.
        role_id: The role to assign.
        assigned_by: The admin identity performing the assignment, if any.
    """

    identity_id: uuid.UUID
    role_id: uuid.UUID
    assigned_by: uuid.UUID | None = None


class AssignRoleHandler:
    """Handles role assignment for an identity.

    Ensures both the identity and role exist, creates the association,
    updates session-level role activations for all active sessions, and
    emits a domain event for downstream cache invalidation.
    """

    def __init__(
        self,
        identity_repo: IIdentityRepository,
        role_repo: IRoleRepository,
        session_repo: ISessionRepository,
        uow: IUnitOfWork,
        permission_resolver: IPermissionResolver,
        logger: ILogger,
    ) -> None:
        self._identity_repo = identity_repo
        self._role_repo = role_repo
        self._session_repo = session_repo
        self._uow = uow
        self._permission_resolver = permission_resolver
        self._logger = logger.bind(handler="AssignRoleHandler")

    async def handle(self, command: AssignRoleCommand) -> None:
        """Execute the role assignment command.

        Args:
            command: The assign role command.

        Raises:
            NotFoundError: If the identity or role does not exist.
        """
        async with self._uow:
            # Validate identity exists
            identity = await self._identity_repo.get(command.identity_id)
            if identity is None:
                raise NotFoundError(
                    message=f"Identity {command.identity_id} not found",
                    error_code="IDENTITY_NOT_FOUND",
                )

            # Validate role exists
            role = await self._role_repo.get(command.role_id)
            if role is None:
                raise NotFoundError(
                    message=f"Role {command.role_id} not found",
                    error_code="ROLE_NOT_FOUND",
                )

            # Static Separation of Duties — data-driven via role.target_account_type
            if (
                role.target_account_type is not None
                and role.target_account_type != identity.account_type
            ):
                raise AccountTypeMismatchError()

            # Assign role to identity
            await self._role_repo.assign_to_identity(
                identity_id=command.identity_id,
                role_id=command.role_id,
                assigned_by=command.assigned_by,
            )

            # Update session_roles for all active sessions (NIST compliance)
            active_session_ids = await self._session_repo.get_active_session_ids(
                command.identity_id,
            )
            for sid in active_session_ids:
                await self._session_repo.add_session_roles(sid, [command.role_id])

            # Emit RoleAssignmentChangedEvent for cache invalidation
            identity.add_domain_event(
                RoleAssignmentChangedEvent(
                    identity_id=command.identity_id,
                    role_id=command.role_id,
                    action="assigned",
                    aggregate_id=str(command.identity_id),
                )
            )
            self._uow.register_aggregate(identity)
            await self._uow.commit()

        # Synchronous cache invalidation OUTSIDE transaction (single round-trip)
        await self._permission_resolver.invalidate_many(active_session_ids)

        self._logger.info(
            "role.assigned",
            identity_id=str(command.identity_id),
            role_id=str(command.role_id),
            role_name=role.name,
            invalidated_sessions=len(active_session_ids),
        )
