"""Commands: mark Recipient verified / invalid (driven by external validators)."""

import uuid
from dataclasses import dataclass

from src.modules.recipient.domain.exceptions import RecipientNotFoundError
from src.modules.recipient.domain.interfaces import IRecipientRepository
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class MarkRecipientVerifiedCommand:
    recipient_id: uuid.UUID


class MarkRecipientVerifiedHandler:
    def __init__(
        self,
        repo: IRecipientRepository,
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
        self._repo = repo
        self._uow = uow
        self._logger = logger.bind(handler="MarkRecipientVerifiedHandler")

    async def handle(self, command: MarkRecipientVerifiedCommand) -> None:
        async with self._uow:
            recipient = await self._repo.get_for_update(command.recipient_id)
            if recipient is None:
                raise RecipientNotFoundError(recipient_id=str(command.recipient_id))
            recipient.mark_verified()
            await self._repo.update(recipient)
            self._uow.register_aggregate(recipient)
            await self._uow.commit()


@dataclass(frozen=True)
class MarkRecipientInvalidCommand:
    recipient_id: uuid.UUID
    reason: str


class MarkRecipientInvalidHandler:
    def __init__(
        self,
        repo: IRecipientRepository,
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
        self._repo = repo
        self._uow = uow
        self._logger = logger.bind(handler="MarkRecipientInvalidHandler")

    async def handle(self, command: MarkRecipientInvalidCommand) -> None:
        async with self._uow:
            recipient = await self._repo.get_for_update(command.recipient_id)
            if recipient is None:
                raise RecipientNotFoundError(recipient_id=str(command.recipient_id))
            recipient.mark_invalid(reason=command.reason)
            await self._repo.update(recipient)
            self._uow.register_aggregate(recipient)
            await self._uow.commit()
