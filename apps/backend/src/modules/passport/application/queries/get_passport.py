"""Query: get a single Passport by id with ownership check."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.passport.application.queries.read_models import PassportReadModel
from src.modules.passport.domain.exceptions import (
    PassportNotFoundError,
    PassportOwnershipMismatchError,
)
from src.modules.passport.infrastructure.models import PassportModel


@dataclass(frozen=True)
class GetPassportQuery:
    passport_id: uuid.UUID
    identity_id: uuid.UUID


class GetPassportHandler:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def handle(self, query: GetPassportQuery) -> PassportReadModel:
        stmt = select(PassportModel).where(PassportModel.id == query.passport_id)
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        if row is None:
            raise PassportNotFoundError(passport_id=str(query.passport_id))
        if row.identity_id != query.identity_id:
            raise PassportOwnershipMismatchError(passport_id=str(query.passport_id))
        return PassportReadModel(
            passport_id=row.id,
            identity_id=row.identity_id,
            full_name_ru=row.full_name_ru,
            full_name_lat=row.full_name_lat,
            passport_serial=row.passport_serial,
            passport_number=row.passport_number,
            passport_issue_date=row.passport_issue_date,
            birth_date=row.birth_date,
            inn=row.inn,
            validation_status=row.validation_status,
            validation_failed_reason=row.validation_failed_reason,
            is_archived=row.is_archived,
            created_at=row.created_at,
            updated_at=row.updated_at,
            version=row.version,
        )
