"""
Query handler: paginated listing of family-attribute exclusions.

Strict CQRS read side -- does not use IUnitOfWork, domain aggregates, or
repositories. Queries the ORM directly via AsyncSession and returns
Pydantic read models.
"""

import uuid
from dataclasses import dataclass

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.infrastructure.models import (
    FamilyAttributeExclusion as OrmExclusion,
)
from src.shared.interfaces.logger import ILogger
from src.shared.pagination import paginate

# ---------------------------------------------------------------------------
# Read Models
# ---------------------------------------------------------------------------


class FamilyExclusionReadModel(BaseModel):
    """Read model for a single family-attribute exclusion."""

    id: uuid.UUID
    family_id: uuid.UUID
    attribute_id: uuid.UUID


class FamilyExclusionListReadModel(BaseModel):
    """Paginated list of family exclusions."""

    items: list[FamilyExclusionReadModel]
    total: int
    offset: int
    limit: int


# ---------------------------------------------------------------------------
# Query
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ListFamilyExclusionsQuery:
    """Pagination parameters for family exclusion listing."""

    family_id: uuid.UUID
    offset: int = 0
    limit: int = 50


# ---------------------------------------------------------------------------
# Handler
# ---------------------------------------------------------------------------


class ListFamilyExclusionsHandler:
    """Fetch a paginated list of attribute exclusions for a family."""

    def __init__(self, session: AsyncSession, logger: ILogger):
        self._session = session
        self._logger = logger.bind(handler="ListFamilyExclusionsHandler")

    async def handle(
        self, query: ListFamilyExclusionsQuery
    ) -> FamilyExclusionListReadModel:
        """Retrieve a paginated exclusion list for a family."""
        base = (
            select(OrmExclusion)
            .where(OrmExclusion.family_id == query.family_id)
            .order_by(OrmExclusion.created_at)
        )

        items, total = await paginate(
            self._session,
            base,
            offset=query.offset,
            limit=query.limit,
            mapper=self._to_read_model,
        )

        return FamilyExclusionListReadModel(
            items=items,
            total=total,
            offset=query.offset,
            limit=query.limit,
        )

    @staticmethod
    def _to_read_model(row: OrmExclusion) -> FamilyExclusionReadModel:
        """Convert an ORM row to a read model."""
        return FamilyExclusionReadModel(
            id=row.id,
            family_id=row.family_id,
            attribute_id=row.attribute_id,
        )
