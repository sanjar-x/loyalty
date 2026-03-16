# src/modules/user/application/commands/update_profile.py
import uuid
from dataclasses import dataclass

from src.modules.user.domain.exceptions import UserNotFoundError
from src.modules.user.domain.interfaces import IUserRepository
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class UpdateProfileCommand:
    user_id: uuid.UUID
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    profile_email: str | None = None


class UpdateProfileHandler:
    def __init__(
        self,
        user_repo: IUserRepository,
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
        self._user_repo = user_repo
        self._uow = uow
        self._logger = logger.bind(handler="UpdateProfileHandler")

    async def handle(self, command: UpdateProfileCommand) -> None:
        async with self._uow:
            user = await self._user_repo.get(command.user_id)
            if user is None:
                raise UserNotFoundError(command.user_id)

            # Build kwargs from non-None fields
            updates = {}
            if command.first_name is not None:
                updates["first_name"] = command.first_name
            if command.last_name is not None:
                updates["last_name"] = command.last_name
            if command.phone is not None:
                updates["phone"] = command.phone
            if command.profile_email is not None:
                updates["profile_email"] = command.profile_email

            if updates:
                user.update_profile(**updates)
                await self._user_repo.update(user)

            await self._uow.commit()

        self._logger.info("user.profile_updated", user_id=str(command.user_id))
