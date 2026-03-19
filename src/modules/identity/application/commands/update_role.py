"""Command handler for updating a role's name and/or description.

Validates role existence, system role name immutability, and name uniqueness
before applying updates.
"""

import uuid
from dataclasses import dataclass

from src.modules.identity.domain.exceptions import SystemRoleModificationError
from src.modules.identity.domain.interfaces import IRoleRepository
from src.shared.exceptions import ConflictError, NotFoundError
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class UpdateRoleCommand:
    """Command to update a role's name and/or description.

    Attributes:
        role_id: The role to update.
        name: New role name, or None to keep current.
        description: New role description, or None to keep current.
    """

    role_id: uuid.UUID
    name: str | None = None
    description: str | None = None


class UpdateRoleResult:
    """Result of the update role command.

    Attributes:
        role_id: The updated role's UUID.
    """

    def __init__(self, role_id: uuid.UUID) -> None:
        self.role_id = role_id


class UpdateRoleHandler:
    """Handles role update with system role protection and uniqueness checks."""

    def __init__(
        self,
        role_repo: IRoleRepository,
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
        self._role_repo = role_repo
        self._uow = uow
        self._logger = logger.bind(handler="UpdateRoleHandler")

    async def handle(self, command: UpdateRoleCommand) -> UpdateRoleResult:
        """Execute the update role command.

        Args:
            command: The update role command.

        Returns:
            The update result with the role ID.

        Raises:
            NotFoundError: If the role does not exist.
            SystemRoleModificationError: If attempting to rename a system role.
            ConflictError: If the new name already exists on a different role.
        """
        async with self._uow:
            # 1. Role exists
            role = await self._role_repo.get(command.role_id)
            if role is None:
                raise NotFoundError(
                    message=f"Role {command.role_id} not found",
                    error_code="ROLE_NOT_FOUND",
                )

            # 2. System role name protection
            if command.name is not None and role.is_system:
                raise SystemRoleModificationError(role_name=role.name)

            # 3. Name uniqueness check
            if command.name is not None:
                existing = await self._role_repo.get_by_name(command.name)
                if existing is not None and existing.id != role.id:
                    raise ConflictError(
                        message=f"Role '{command.name}' already exists",
                        error_code="ROLE_ALREADY_EXISTS",
                    )

            # 4. Apply updates
            if command.name is not None:
                role.name = command.name
            if command.description is not None:
                role.description = command.description

            # 5. Persist
            await self._role_repo.update(role)
            await self._uow.commit()

        self._logger.info(
            "role.updated",
            role_id=str(command.role_id),
            name=command.name,
            description=command.description,
        )

        return UpdateRoleResult(role_id=command.role_id)
