# src/modules/identity/application/commands/assign_role.py
import uuid
from dataclasses import dataclass

from src.modules.identity.domain.events import RoleAssignmentChangedEvent
from src.modules.identity.domain.interfaces import (
    IIdentityRepository,
    IRoleRepository,
    ISessionRepository,
)
from src.shared.exceptions import NotFoundError
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class AssignRoleCommand:
    identity_id: uuid.UUID
    role_id: uuid.UUID
    assigned_by: uuid.UUID | None = None


class AssignRoleHandler:
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
        self._logger = logger.bind(handler="AssignRoleHandler")

    async def handle(self, command: AssignRoleCommand) -> None:
        async with self._uow:
            # 1. Validate identity exists
            identity = await self._identity_repo.get(command.identity_id)
            if identity is None:
                raise NotFoundError(
                    message=f"Identity {command.identity_id} not found",
                    error_code="IDENTITY_NOT_FOUND",
                )

            # 2. Validate role exists
            role = await self._role_repo.get(command.role_id)
            if role is None:
                raise NotFoundError(
                    message=f"Role {command.role_id} not found",
                    error_code="ROLE_NOT_FOUND",
                )

            # 3. Assign role to identity
            await self._role_repo.assign_to_identity(
                identity_id=command.identity_id,
                role_id=command.role_id,
                assigned_by=command.assigned_by,
            )

            # 4. Update session_roles for ALL active sessions (NIST compliance)
            active_session_ids = await self._session_repo.get_active_session_ids(
                command.identity_id,
            )
            for sid in active_session_ids:
                await self._session_repo.add_session_roles(sid, [command.role_id])

            # 5. Emit RoleAssignmentChangedEvent (for cache invalidation)
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

        self._logger.info(
            "role.assigned",
            identity_id=str(command.identity_id),
            role_id=str(command.role_id),
            role_name=role.name,
        )
