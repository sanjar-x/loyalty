"""Command: soft-delete (archive) a recipient."""

import uuid
from dataclasses import dataclass

from src.modules.recipient.domain.exceptions import (
    RecipientNotFoundError,
    RecipientOwnershipError,
)
from src.modules.recipient.domain.interfaces import IRecipientRepository
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class ArchiveRecipientCommand:
    recipient_id: uuid.UUID
    identity_id: uuid.UUID


class ArchiveRecipientHandler:
    def __init__(
        self,
        repo: IRecipientRepository,
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
        self._repo = repo
        self._uow = uow
        self._logger = logger.bind(handler="ArchiveRecipientHandler")

    async def handle(self, command: ArchiveRecipientCommand) -> None:
        async with self._uow:
            recipient = await self._repo.get_for_update(command.recipient_id)
            if recipient is None:
                raise RecipientNotFoundError(recipient_id=str(command.recipient_id))
            if recipient.identity_id != command.identity_id:
                raise RecipientOwnershipError(recipient_id=str(command.recipient_id))
            recipient.archive()
            await self._repo.update(recipient)
            self._uow.register_aggregate(recipient)
            await self._uow.commit()
            self._logger.info("recipient.archived", recipient_id=str(recipient.id))
