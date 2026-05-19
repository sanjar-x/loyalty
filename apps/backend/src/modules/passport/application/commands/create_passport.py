"""Command: customer creates a new Passport."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date

from src.modules.passport.domain.entities import Passport
from src.modules.passport.domain.interfaces import IPassportRepository
from src.modules.passport.domain.value_objects import CustomsData, FullName
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class CreatePassportCommand:
    identity_id: uuid.UUID
    full_name_ru: str
    full_name_lat: str
    passport_serial: str
    passport_number: str
    passport_issue_date: date
    birth_date: date
    inn: str


@dataclass(frozen=True)
class CreatePassportResult:
    passport_id: uuid.UUID


class CreatePassportHandler:
    def __init__(
        self,
        repo: IPassportRepository,
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
        self._repo = repo
        self._uow = uow
        self._logger = logger.bind(handler="CreatePassportHandler")

    async def handle(self, command: CreatePassportCommand) -> CreatePassportResult:
        async with self._uow:
            full_name = FullName.parse(
                ru=command.full_name_ru, lat=command.full_name_lat
            )
            customs = CustomsData.parse(
                passport_serial=command.passport_serial,
                passport_number=command.passport_number,
                passport_issue_date=command.passport_issue_date,
                birth_date=command.birth_date,
                inn=command.inn,
            )
            passport = Passport.create(
                identity_id=command.identity_id,
                full_name=full_name,
                customs_data=customs,
            )
            await self._repo.add(passport)
            self._uow.register_aggregate(passport)
            await self._uow.commit()
            self._logger.info(
                "passport.created",
                passport_id=str(passport.id),
                identity_id=str(command.identity_id),
            )
            return CreatePassportResult(passport_id=passport.id)
