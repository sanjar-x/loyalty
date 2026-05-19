"""Command: update an existing Recipient.

Post-Sprint-1.5 Part 2: customs fields removed from the payload —
they live on Passport now. Recipient holds shipping coordinates only.
Ownership of the recipient is enforced by ``identity_id`` match
(mismatch → 404). Optional ``expected_version`` preserves the
ETag / If-Match optimistic-locking contract.
"""

import uuid
from dataclasses import dataclass

from src.modules.recipient.domain.exceptions import (
    RecipientNotFoundError,
    RecipientOwnershipError,
)
from src.modules.recipient.domain.interfaces import IRecipientRepository
from src.modules.recipient.domain.value_objects import Email, FullName, Phone
from src.shared.exceptions import OptimisticLockError
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
    expected_version: int | None = None
    """D0.3 — when set, the handler enforces optimistic locking before
    mutating: aggregate ``version`` mismatch raises
    :class:`OptimisticLockError`. ``None`` (default) keeps the legacy
    last-write-wins behaviour for clients that haven't adopted ETag /
    If-Match yet."""


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

            if (
                command.expected_version is not None
                and command.expected_version != recipient.version
            ):
                raise OptimisticLockError(
                    entity_type="Recipient",
                    entity_id=recipient.id,
                    expected_version=command.expected_version,
                    actual_version=recipient.version,
                )

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
            recipient.update(
                full_name=full_name,
                phone=phone,
                email=email,
            )
            await self._repo.update(recipient)
            self._uow.register_aggregate(recipient)
            await self._uow.commit()
            self._logger.info("recipient.updated", recipient_id=str(recipient.id))
