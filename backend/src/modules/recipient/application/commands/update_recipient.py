"""Command: update an existing Recipient.

Editing customs data resets ``validation_status`` to PENDING — DobroPost
will revalidate on the next cross-border attempt. Ownership of the
recipient is enforced by ``identity_id`` match (mismatch → 404).
"""

import uuid
from dataclasses import dataclass
from datetime import date

from src.modules.recipient.domain.exceptions import (
    RecipientNotFoundError,
    RecipientOwnershipError,
)
from src.modules.recipient.domain.interfaces import IRecipientRepository
from src.modules.recipient.domain.value_objects import (
    CustomsData,
    Email,
    FullName,
    Phone,
)
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class UpdateRecipientCommand:
    recipient_id: uuid.UUID
    identity_id: uuid.UUID
    full_name_ru: str | None = None
    full_name_lat: str | None = None
    phone: str | None = None
    email: str | None = None
    passport_serial: str | None = None
    passport_number: str | None = None
    passport_issue_date: date | None = None
    birth_date: date | None = None
    inn: str | None = None


class UpdateRecipientHandler:
    def __init__(
        self,
        repo: IRecipientRepository,
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
        self._repo = repo
        self._uow = uow
        self._logger = logger.bind(handler="UpdateRecipientHandler")

    async def handle(self, command: UpdateRecipientCommand) -> None:
        async with self._uow:
            recipient = await self._repo.get_for_update(command.recipient_id)
            if recipient is None:
                raise RecipientNotFoundError(recipient_id=str(command.recipient_id))
            if recipient.identity_id != command.identity_id:
                raise RecipientOwnershipError(recipient_id=str(command.recipient_id))

            full_name = (
                FullName.parse(
                    ru=command.full_name_ru or recipient.full_name.ru,
                    lat=command.full_name_lat or recipient.full_name.lat,
                )
                if (command.full_name_ru or command.full_name_lat)
                else None
            )
            phone = Phone.parse(command.phone) if command.phone else None
            email = Email.parse(command.email) if command.email else None
            customs_data = (
                CustomsData.parse(
                    passport_serial=command.passport_serial
                    or recipient.customs_data.passport_serial,
                    passport_number=command.passport_number
                    or recipient.customs_data.passport_number,
                    passport_issue_date=command.passport_issue_date
                    or recipient.customs_data.passport_issue_date,
                    birth_date=command.birth_date or recipient.customs_data.birth_date,
                    inn=command.inn or recipient.customs_data.inn,
                )
                if (
                    command.passport_serial
                    or command.passport_number
                    or command.passport_issue_date
                    or command.birth_date
                    or command.inn
                )
                else None
            )
            recipient.update(
                full_name=full_name,
                phone=phone,
                email=email,
                customs_data=customs_data,
            )
            await self._repo.update(recipient)
            self._uow.register_aggregate(recipient)
            await self._uow.commit()
            self._logger.info("recipient.updated", recipient_id=str(recipient.id))
