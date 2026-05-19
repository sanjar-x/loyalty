"""Query: list passports owned by the authenticated identity."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.passport.application.queries.read_models import PassportReadModel
from src.modules.passport.infrastructure.models import PassportModel


@dataclass(frozen=True)
class ListMyPassportsQuery:
    identity_id: uuid.UUID
    include_archived: bool = False


@dataclass(frozen=True)
class ListMyPassportsPage:
    items: list[PassportReadModel]


class ListMyPassportsHandler:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def handle(self, query: ListMyPassportsQuery) -> ListMyPassportsPage:
        stmt = (
            select(PassportModel)
            .where(PassportModel.identity_id == query.identity_id)
            .order_by(PassportModel.created_at.desc())
        )
        if not query.include_archived:
            stmt = stmt.where(PassportModel.is_archived.is_(False))
        rows = (await self._session.execute(stmt)).scalars().all()
        return ListMyPassportsPage(
            items=[
                PassportReadModel(
                    passport_id=r.id,
                    identity_id=r.identity_id,
                    full_name_ru=r.full_name_ru,
                    full_name_lat=r.full_name_lat,
                    passport_serial=r.passport_serial,
                    passport_number=r.passport_number,
                    passport_issue_date=r.passport_issue_date,
                    birth_date=r.birth_date,
                    inn=r.inn,
                    validation_status=r.validation_status,
                    validation_failed_reason=r.validation_failed_reason,
                    is_archived=r.is_archived,
                    created_at=r.created_at,
                    updated_at=r.updated_at,
                    version=r.version,
                )
                for r in rows
            ]
        )
