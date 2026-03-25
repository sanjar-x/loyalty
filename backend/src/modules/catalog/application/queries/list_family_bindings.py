"""
Query handler: paginated listing of family-attribute bindings.

Strict CQRS read side -- does not use IUnitOfWork, domain aggregates, or
repositories. Queries the ORM directly via AsyncSession and returns
Pydantic read models.
"""

import uuid
from dataclasses import dataclass

from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.infrastructure.models import (
    FamilyAttributeBinding as OrmBinding,
)
from src.shared.interfaces.logger import ILogger


# ---------------------------------------------------------------------------
# Read Models
# ---------------------------------------------------------------------------


class FamilyBindingReadModel(BaseModel):
    """Read model for a single family-attribute binding."""

    id: uuid.UUID
    family_id: uuid.UUID
    attribute_id: uuid.UUID
    sort_order: int
    requirement_level: str
    flag_overrides: dict | None = None
    filter_settings: dict | None = None


class FamilyBindingListReadModel(BaseModel):
    """Paginated list of family bindings."""

    items: list[FamilyBindingReadModel]
    total: int
    offset: int
    limit: int


# ---------------------------------------------------------------------------
# Query
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ListFamilyBindingsQuery:
    """Pagination parameters for family binding listing."""

    family_id: uuid.UUID
    offset: int = 0
    limit: int = 50


# ---------------------------------------------------------------------------
# Handler
# ---------------------------------------------------------------------------


class ListFamilyBindingsHandler:
    """Fetch a paginated list of attribute bindings for a family."""

    def __init__(self, session: AsyncSession, logger: ILogger):
        self._session = session
        self._logger = logger.bind(handler="ListFamilyBindingsHandler")

    async def handle(
        self, query: ListFamilyBindingsQuery
    ) -> FamilyBindingListReadModel:
        """Retrieve a paginated binding list for a family."""
        count_result = await self._session.execute(
            select(func.count())
            .select_from(OrmBinding)
            .where(OrmBinding.family_id == query.family_id)
        )
        total: int = count_result.scalar_one()

        stmt = (
            select(OrmBinding)
            .where(OrmBinding.family_id == query.family_id)
            .order_by(OrmBinding.sort_order)
            .limit(query.limit)
            .offset(query.offset)
        )
        result = await self._session.execute(stmt)
        rows = result.scalars().all()

        items = [
            FamilyBindingReadModel(
                id=row.id,
                family_id=row.family_id,
                attribute_id=row.attribute_id,
                sort_order=row.sort_order,
                requirement_level=row.requirement_level.value,
                flag_overrides=dict(row.flag_overrides) if row.flag_overrides else None,
                filter_settings=dict(row.filter_settings) if row.filter_settings else None,
            )
            for row in rows
        ]

        return FamilyBindingListReadModel(
            items=items,
            total=total,
            offset=query.offset,
            limit=query.limit,
        )
