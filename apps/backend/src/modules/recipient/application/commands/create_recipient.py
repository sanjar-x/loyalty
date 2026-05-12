"""Command: create a new Recipient owned by ``identity_id``.

Format-level validation runs synchronously inside ``CustomsData.parse``
and the small VOs. External (DaData) validation is deferred to the
DobroPost cross-border step (research §10.5.1) — at create time we
record the recipient with ``validation_status=PENDING``. Customers can
checkout against PENDING recipients; if customs later rejects passport,
Order moves to ON_HOLD.
"""

import uuid
from dataclasses import dataclass
from datetime import date

from src.modules.recipient.domain.entities import Recipient
from src.modules.recipient.domain.interfaces import IRecipientRepository
from src.modules.recipient.domain.value_objects import (
    CustomsData,
    Email,
    FullName,
    Phone,
)
from shared.interfaces.logger import ILogger
from shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class CreateRecipientCommand:
    identity_id: uuid.UUID
    full_name_ru: str
    full_name_lat: str
    phone: str
    email: str
    passport_serial: str
    passport_number: str
    passport_issue_date: date
    birth_date: date
    inn: str


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
                customs_data=CustomsData.parse(
                    passport_serial=command.passport_serial,
                    passport_number=command.passport_number,
                    passport_issue_date=command.passport_issue_date,
                    birth_date=command.birth_date,
                    inn=command.inn,
                ),
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
