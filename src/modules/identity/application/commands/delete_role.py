# src/modules/identity/application/commands/delete_role.py
import uuid
from dataclasses import dataclass

from src.modules.identity.domain.exceptions import SystemRoleModificationError
from src.modules.identity.domain.interfaces import IRoleRepository
from src.shared.exceptions import NotFoundError
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class DeleteRoleCommand:
    role_id: uuid.UUID


class DeleteRoleHandler:
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
