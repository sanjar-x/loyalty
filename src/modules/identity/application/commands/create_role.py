# src/modules/identity/application/commands/create_role.py
import uuid
from dataclasses import dataclass

from src.modules.identity.domain.entities import Role
from src.modules.identity.domain.interfaces import IRoleRepository
from src.shared.exceptions import ConflictError
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class CreateRoleCommand:
    name: str
    description: str | None = None


@dataclass(frozen=True)
class CreateRoleResult:
    role_id: uuid.UUID


class CreateRoleHandler:
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
