"""Command: create a new Recipient owned by ``identity_id``.

Post-Sprint-1.5 Part 2 (ADR-011): customs identifiers (passport,
INN, birth_date) live in the separate ``passport`` bounded context.
Recipient holds shipping coordinates only — name + phone + email —
and no validation FSM (shipping data is a destination, not a
document).
"""

import uuid
from dataclasses import dataclass

from src.modules.recipient.domain.entities import Recipient
from src.modules.recipient.domain.interfaces import IRecipientRepository
from src.modules.recipient.domain.value_objects import Email, FullName, Phone
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class CreateRecipientCommand:
    identity_id: uuid.UUID
    full_name_ru: str
    full_name_lat: str
    phone: str
    email: str


@dataclass(frozen=True)
class CreateRecipientResult:
    recipient_id: uuid.UUID


class CreateRecipientHandler:
    def __init__(
        self,
        repo: IRecipientRepository,
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
        self._repo = repo
        self._uow = uow
        self._logger = logger.bind(handler="CreateRecipientHandler")

    async def handle(self, command: CreateRecipientCommand) -> CreateRecipientResult:
        async with self._uow:
            recipient = Recipient.create(
                identity_id=command.identity_id,
                full_name=FullName.parse(
                    ru=command.full_name_ru, lat=command.full_name_lat
                ),
                phone=Phone.parse(command.phone),
                email=Email.parse(command.email),
            )
            recipient = await self._repo.add(recipient)
            self._uow.register_aggregate(recipient)
            await self._uow.commit()
            self._logger.info(
                "recipient.created",
                recipient_id=str(recipient.id),
                identity_id=str(command.identity_id),
            )
            return CreateRecipientResult(recipient_id=recipient.id)
