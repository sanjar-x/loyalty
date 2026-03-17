"""Command handler for deleting a custom RBAC role.

Validates that the role exists and is not a system role before deletion.
"""

import uuid
from dataclasses import dataclass

from src.modules.identity.domain.exceptions import SystemRoleModificationError
from src.modules.identity.domain.interfaces import IRoleRepository
from src.shared.exceptions import NotFoundError
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class DeleteRoleCommand:
    """Command to delete a role by its identifier.

    Attributes:
        role_id: The UUID of the role to delete.
    """

    role_id: uuid.UUID


class DeleteRoleHandler:
    """Handles deletion of custom (non-system) roles."""

    def __init__(
        self,
        role_repo: IRoleRepository,
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
        self._role_repo = role_repo
        self._uow = uow
        self._logger = logger.bind(handler="DeleteRoleHandler")

    async def handle(self, command: DeleteRoleCommand) -> None:
        """Execute the delete role command.

        Args:
            command: The delete role command.

        Raises:
            NotFoundError: If the role does not exist.
            SystemRoleModificationError: If the role is a system role.
        """
        async with self._uow:
            role = await self._role_repo.get(command.role_id)
            if role is None:
                raise NotFoundError(
                    message=f"Role {command.role_id} not found",
                    error_code="ROLE_NOT_FOUND",
                )

            if role.is_system:
                raise SystemRoleModificationError(role_name=role.name)

            await self._role_repo.delete(command.role_id)
            await self._uow.commit()

        self._logger.info(
            "role.deleted",
            role_id=str(command.role_id),
            name=role.name,
        )
