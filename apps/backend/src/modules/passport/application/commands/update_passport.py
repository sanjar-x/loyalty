"""Command: customer updates an existing Passport.

Re-parses any field provided (so format errors surface as 400 with
the same error code as create), enforces ownership boundary
(``passport.identity_id == command.identity_id``), and delegates the
domain-level «customs changed → reset validation» semantics to
``Passport.update``.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date

from src.modules.passport.domain.exceptions import (
    PassportNotFoundError,
    PassportOwnershipMismatchError,
)
from src.modules.passport.domain.interfaces import IPassportRepository
from src.modules.passport.domain.value_objects import CustomsData, FullName
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class UpdatePassportCommand:
    passport_id: uuid.UUID
    identity_id: uuid.UUID
    full_name_ru: str | None = None
    full_name_lat: str | None = None
    passport_serial: str | None = None
    passport_number: str | None = None
    passport_issue_date: date | None = None
    birth_date: date | None = None
    inn: str | None = None


class UpdatePassportHandler:
    def __init__(
        self,
        repo: IPassportRepository,
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
        self._repo = repo
        self._uow = uow
        self._logger = logger.bind(handler="UpdatePassportHandler")

    async def handle(self, command: UpdatePassportCommand) -> None:
        async with self._uow:
            passport = await self._repo.get_for_update(command.passport_id)
            if passport is None:
                raise PassportNotFoundError(passport_id=str(command.passport_id))
            if passport.identity_id != command.identity_id:
                raise PassportOwnershipMismatchError(
                    passport_id=str(command.passport_id)
                )

            new_name: FullName | None = None
            if command.full_name_ru is not None or command.full_name_lat is not None:
                new_name = FullName.parse(
                    ru=command.full_name_ru or passport.full_name.ru,
                    lat=command.full_name_lat or passport.full_name.lat,
                )

            new_customs: CustomsData | None = None
            if any(
                v is not None
                for v in (
                    command.passport_serial,
                    command.passport_number,
                    command.passport_issue_date,
                    command.birth_date,
                    command.inn,
                )
            ):
                new_customs = CustomsData.parse(
                    passport_serial=command.passport_serial
                    or passport.customs_data.passport_serial,
                    passport_number=command.passport_number
                    or passport.customs_data.passport_number,
                    passport_issue_date=command.passport_issue_date
                    or passport.customs_data.passport_issue_date,
                    birth_date=command.birth_date or passport.customs_data.birth_date,
                    inn=command.inn or passport.customs_data.inn,
                )

            passport.update(full_name=new_name, customs_data=new_customs)
            await self._repo.update(passport)
            self._uow.register_aggregate(passport)
            await self._uow.commit()
            self._logger.info(
                "passport.updated",
                passport_id=str(passport.id),
                identity_id=str(command.identity_id),
            )
