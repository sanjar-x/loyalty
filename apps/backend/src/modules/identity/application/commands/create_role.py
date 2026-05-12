"""Command handler for creating a new custom RBAC role.

Validates uniqueness of the role name and persists a new non-system role.
"""

import uuid
from dataclasses import dataclass

from src.modules.identity.domain.entities import Role
from src.modules.identity.domain.interfaces import IRoleRepository
from src.shared.exceptions import ConflictError
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class CreateRoleCommand:
    """Command to create a new custom role.

    Attributes:
        name: Unique role name (lowercase, underscores).
        description: Optional human-readable description.
    """

    name: str
    description: str | None = None


@dataclass(frozen=True)
class CreateRoleResult:
    """Result of a successful role creation.

    Attributes:
        role_id: The UUID of the newly created role.
    """

    role_id: uuid.UUID


class CreateRoleHandler:
    """Handles creation of new custom RBAC roles."""

    def __init__(
        self,
        role_repo: IRoleRepository,
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
        self._role_repo = role_repo
        self._uow = uow
        self._logger = logger.bind(handler="CreateRoleHandler")

    async def handle(self, command: CreateRoleCommand) -> CreateRoleResult:
        """Execute the create role command.

        Args:
            command: The create role command.

        Returns:
            A result containing the new role's UUID.

        Raises:
            ConflictError: If a role with the same name already exists.
        """
        async with self._uow:
            existing = await self._role_repo.get_by_name(command.name)
            if existing:
                raise ConflictError(
                    message=f"Role '{command.name}' already exists",
                    error_code="ROLE_ALREADY_EXISTS",
                )

            role = Role(
                id=uuid.uuid7() if hasattr(uuid, "uuid7") else uuid.uuid4(),
                name=command.name,
                description=command.description,
                is_system=False,
            )
            await self._role_repo.add(role)
            await self._uow.commit()

        self._logger.info("role.created", role_id=str(role.id), name=role.name)
        return CreateRoleResult(role_id=role.id)
