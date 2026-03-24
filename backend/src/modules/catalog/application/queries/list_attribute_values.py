"""
Query handler: paginated attribute value listing with search.

Strict CQRS read side -- queries the ORM directly and returns read models.
Supports search by value_i18n and search_aliases across all languages.
"""

import uuid
from dataclasses import dataclass

from sqlalchemy import Select, Text, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.application.queries.read_models import (
    AttributeValueListReadModel,
    AttributeValueReadModel,
)
from src.modules.catalog.infrastructure.models import (
    AttributeValue as OrmAttributeValue,
)
from src.shared.interfaces.logger import ILogger


@dataclass(frozen=True)
class ListAttributeValuesQuery:
    """Pagination and filter parameters for attribute value listing.

    Attributes:
        attribute_id: UUID of the parent attribute (required).
        offset: Number of records to skip.
        limit: Maximum number of records to return.
        search: Search term to match against value_i18n.
    """

    attribute_id: uuid.UUID
    offset: int = 0
    limit: int = 100
    search: str | None = None


class ListAttributeValuesHandler:
    """Fetch a paginated list of attribute values for a given attribute."""

    def __init__(self, session: AsyncSession, logger: ILogger):
        self._session = session
        self._logger = logger.bind(handler="ListAttributeValuesHandler")

    async def handle(
        self, query: ListAttributeValuesQuery
    ) -> AttributeValueListReadModel:
        """Retrieve a paginated attribute value list with optional search.

        Args:
            query: Pagination and filter parameters.

        Returns:
            Paginated list read model with items and total count.
        """
        base = select(OrmAttributeValue).where(
            OrmAttributeValue.attribute_id == query.attribute_id
        )

        if query.search:
            base = self._apply_search(base, query.search)

        # Count
        count_stmt = select(func.count()).select_from(base.subquery())
        count_result = await self._session.execute(count_stmt)
        total: int = count_result.scalar_one()

        # Items
        items_stmt = (
            base.order_by(OrmAttributeValue.sort_order, OrmAttributeValue.code)
            .offset(query.offset)
            .limit(query.limit)
        )
        result = await self._session.execute(items_stmt)
        rows = result.scalars().all()

        items = [self._to_read_model(orm) for orm in rows]

        return AttributeValueListReadModel(
            items=items,
            total=total,
            offset=query.offset,
            limit=query.limit,
        )

    @staticmethod
    def _apply_search(
        stmt: Select[tuple[OrmAttributeValue]], search: str
    ) -> Select[tuple[OrmAttributeValue]]:
        """Apply full-text search across value_i18n values."""
        escaped = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        pattern = f"%{escaped}%"
        stmt = stmt.where(
            func.cast(OrmAttributeValue.value_i18n, Text()).ilike(pattern)
        )
        return stmt

    @staticmethod
    def _to_read_model(orm: OrmAttributeValue) -> AttributeValueReadModel:
        """Convert an ORM row to a read model."""
        return AttributeValueReadModel(
            id=orm.id,
            attribute_id=orm.attribute_id,
            code=orm.code,
            slug=orm.slug,
            value_i18n=orm.value_i18n,
            search_aliases=list(orm.search_aliases) if orm.search_aliases else [],
            meta_data=orm.meta_data,
            value_group=orm.value_group,
            sort_order=orm.sort_order,
        )
