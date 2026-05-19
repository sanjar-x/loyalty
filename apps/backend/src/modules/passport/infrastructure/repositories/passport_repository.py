"""Data Mapper for the Passport aggregate."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.passport.domain.entities import Passport
from src.modules.passport.domain.interfaces import IPassportRepository
from src.modules.passport.domain.value_objects import (
    CustomsData,
    FullName,
    PassportValidationStatus,
)
from src.modules.passport.infrastructure.models import PassportModel


class PassportRepository(IPassportRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, passport: Passport) -> Passport:
        row = _to_orm(passport)
        self._session.add(row)
        await self._session.flush()
        return passport

    async def get(self, passport_id: uuid.UUID) -> Passport | None:
        row = await self._session.get(PassportModel, passport_id)
        return _to_domain(row) if row else None

    async def get_for_update(self, passport_id: uuid.UUID) -> Passport | None:
        stmt = (
            select(PassportModel)
            .where(PassportModel.id == passport_id)
            .with_for_update()
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return _to_domain(row) if row else None

    async def update(self, passport: Passport) -> Passport:
        stmt = select(PassportModel).where(PassportModel.id == passport.id)
        row = (await self._session.execute(stmt)).scalar_one()
        row.full_name_ru = passport.full_name.ru
        row.full_name_lat = passport.full_name.lat
        row.passport_serial = passport.customs_data.passport_serial
        row.passport_number = passport.customs_data.passport_number
        row.passport_issue_date = passport.customs_data.passport_issue_date
        row.birth_date = passport.customs_data.birth_date
        row.inn = passport.customs_data.inn
        row.validation_status = passport.validation_status.value
        row.validation_failed_reason = passport.validation_failed_reason
        row.is_archived = passport.is_archived
        row.version = passport.version + 1
        row.updated_at = passport.updated_at
        await self._session.flush()
        return passport

    async def list_by_identity(
        self,
        identity_id: uuid.UUID,
        *,
        include_archived: bool = False,
    ) -> list[Passport]:
        stmt = (
            select(PassportModel)
            .where(PassportModel.identity_id == identity_id)
            .order_by(PassportModel.created_at.desc())
        )
        if not include_archived:
            stmt = stmt.where(PassportModel.is_archived.is_(False))
        rows = (await self._session.execute(stmt)).scalars().all()
        return [_to_domain(r) for r in rows]


def _to_orm(passport: Passport) -> PassportModel:
    return PassportModel(
        id=passport.id,
        identity_id=passport.identity_id,
        full_name_ru=passport.full_name.ru,
        full_name_lat=passport.full_name.lat,
        passport_serial=passport.customs_data.passport_serial,
        passport_number=passport.customs_data.passport_number,
        passport_issue_date=passport.customs_data.passport_issue_date,
        birth_date=passport.customs_data.birth_date,
        inn=passport.customs_data.inn,
        validation_status=passport.validation_status.value,
        validation_failed_reason=passport.validation_failed_reason,
        is_archived=passport.is_archived,
        version=passport.version,
        created_at=passport.created_at,
        updated_at=passport.updated_at,
    )


def _to_domain(row: PassportModel) -> Passport:
    return Passport(
        id=row.id,
        identity_id=row.identity_id,
        full_name=FullName(ru=row.full_name_ru, lat=row.full_name_lat),
        customs_data=CustomsData(
            passport_serial=row.passport_serial,
            passport_number=row.passport_number,
            passport_issue_date=row.passport_issue_date,
            birth_date=row.birth_date,
            inn=row.inn,
        ),
        validation_status=PassportValidationStatus(row.validation_status),
        validation_failed_reason=row.validation_failed_reason,
        is_archived=row.is_archived,
        created_at=row.created_at,
        updated_at=row.updated_at,
        version=row.version,
    )
