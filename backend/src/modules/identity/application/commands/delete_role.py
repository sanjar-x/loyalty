"""Command handler for deleting a custom RBAC role.

Validates that the role exists and is not a system role before deletion.
Collects affected session IDs and invalidates their permission caches
after the role is removed.
"""

import uuid
from dataclasses import dataclass

from src.modules.identity.domain.exceptions import SystemRoleModificationError
from src.modules.identity.domain.interfaces import (
    IRoleRepository,
    ISessionRepository,
)
from src.shared.exceptions import NotFoundError
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.security import IPermissionResolver
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class DeleteRoleCommand:
    """Command to delete a role by its identifier.

    Attributes:
        role_id: The UUID of the role to delete.
    """

    role_id: uuid.UUID


class DeleteRoleHandler:
    """Handles deletion of custom (non-system) roles with cache invalidation."""

    def __init__(
        self,
        role_repo: IRoleRepository,
        session_repo: ISessionRepository,
        uow: IUnitOfWork,
        permission_resolver: IPermissionResolver,
        logger: ILogger,
    ) -> None:
        self._role_repo = role_repo
        self._session_repo = session_repo
        self._uow = uow
        self._permission_resolver = permission_resolver
        self._logger = logger.bind(handler="DeleteRoleHandler")

    async def handle(self, command: DeleteRoleCommand) -> None:
        """Execute the delete role command.

        Args:
            command: The delete role command.

        Raises:
            NotFoundError: If the role does not exist.
            SystemRoleModificationError: If the role is a system role.
        """
        affected_session_ids: list[uuid.UUID] = []

        async with self._uow:
            role = await self._role_repo.get(command.role_id)
            if role is None:
                raise NotFoundError(
                    message=f"Role {command.role_id} not found",
                    error_code="ROLE_NOT_FOUND",
                )

            if role.is_system:
                raise SystemRoleModificationError(role_name=role.name)

            # Collect affected sessions BEFORE deletion (inside UoW)
            affected_identity_ids = await self._role_repo.get_identity_ids_with_role(
                command.role_id,
            )
            for identity_id in affected_identity_ids:
                session_ids = await self._session_repo.get_active_session_ids(identity_id)
                affected_session_ids.extend(session_ids)

            await self._role_repo.delete(command.role_id)
            await self._uow.commit()

        # Invalidate permission cache OUTSIDE transaction (single round-trip)
        await self._permission_resolver.invalidate_many(affected_session_ids)

        self._logger.info(
            "role.deleted",
            role_id=str(command.role_id),
            name=role.name,
            affected_sessions=len(affected_session_ids),
        )
