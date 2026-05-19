"""ACL adapter: order → passport (ADR-011 / Sprint 1.5 Part 2).

The only file in the order module allowed to import the passport
module's ORM — narrowly whitelisted in tests/architecture as
``("order","passport")``. Reads the ``passports`` table directly
(CQRS read-side) and projects into the order-side
``PassportLookupResult``.

Ownership boundary (``passport.identity_id == auth.identity_id``)
is checked by the handler — the adapter returns whatever the DB
holds; surfacing ownership mismatch as 404 vs 422 is a presentation-
layer concern (mirrors the recipient adapter contract).
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.order.domain.interfaces import (
    IPassportLookup,
    PassportLookupResult,
)
from src.modules.passport.infrastructure.models import PassportModel


class PassportLookupAdapter(IPassportLookup):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, passport_id: uuid.UUID) -> PassportLookupResult | None:
        stmt = select(PassportModel).where(PassportModel.id == passport_id)
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        if row is None:
            return None
        return PassportLookupResult(
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
            is_archived=row.is_archived,
        )
