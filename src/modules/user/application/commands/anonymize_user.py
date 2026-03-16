# src/modules/user/application/commands/anonymize_user.py
import uuid
from dataclasses import dataclass

from src.modules.user.domain.interfaces import IUserRepository
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class AnonymizeUserCommand:
    user_id: uuid.UUID


class AnonymizeUserHandler:
    """GDPR: anonymize PII on IdentityDeactivatedEvent."""

    def __init__(
        self,
        user_repo: IUserRepository,
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
        self._user_repo = user_repo
        self._uow = uow
        self._logger = logger.bind(handler="AnonymizeUserHandler")

    async def handle(self, command: AnonymizeUserCommand) -> None:
        async with self._uow:
            user = await self._user_repo.get(command.user_id)
            if user is None:
                self._logger.warning(
                    "user.not_found_for_anonymization",
                    user_id=str(command.user_id),
                )
                return  # Idempotent

            user.anonymize()
            await self._user_repo.update(user)
            await self._uow.commit()

        self._logger.info(
            "user.anonymized",
            user_id=str(command.user_id),
        )
