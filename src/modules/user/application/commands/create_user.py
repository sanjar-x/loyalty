# src/modules/user/application/commands/create_user.py
import uuid
from dataclasses import dataclass

from src.modules.user.domain.entities import User
from src.modules.user.domain.interfaces import IUserRepository
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class CreateUserCommand:
    identity_id: uuid.UUID
    profile_email: str | None = None


class CreateUserHandler:
    """Internal handler: creates User on IdentityRegisteredEvent via outbox consumer."""

    def __init__(
        self,
        user_repo: IUserRepository,
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
        self._user_repo = user_repo
        self._uow = uow
        self._logger = logger.bind(handler="CreateUserHandler")

    async def handle(self, command: CreateUserCommand) -> None:
        async with self._uow:
            existing = await self._user_repo.get(command.identity_id)
            if existing:
                self._logger.warning(
                    "user.already_exists",
                    identity_id=str(command.identity_id),
                )
                return  # Idempotent: skip if user already created

            user = User.create_from_identity(
                identity_id=command.identity_id,
                profile_email=command.profile_email,
            )
            await self._user_repo.add(user)
            await self._uow.commit()

        self._logger.info(
            "user.created",
            user_id=str(command.identity_id),
        )
