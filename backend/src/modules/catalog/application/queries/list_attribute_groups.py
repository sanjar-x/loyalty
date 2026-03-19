"""
Query handler: paginated attribute group listing.

Strict CQRS read side -- does not use IUnitOfWork, domain aggregates, or
repositories. Queries the database directly via AsyncSession + raw SQL
and returns a Pydantic read model.
"""

from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.application.queries.read_models import (
    AttributeGroupListReadModel,
    AttributeGroupReadModel,
)

_LIST_ATTRIBUTE_GROUPS_SQL = text(
    "SELECT id, code, name_i18n, sort_order "
    "FROM attribute_groups "
    "ORDER BY sort_order, code "
    "LIMIT :limit OFFSET :offset"
)

_COUNT_ATTRIBUTE_GROUPS_SQL = text("SELECT count(*) FROM attribute_groups")


@dataclass(frozen=True)
class ListAttributeGroupsQuery:
    """Pagination parameters for attribute group listing.

    Attributes:
        offset: Number of records to skip.
        limit: Maximum number of records to return.
    """

    offset: int = 0
    limit: int = 50


class ListAttributeGroupsHandler:
    """Fetch a paginated list of attribute groups."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def handle(self, query: ListAttributeGroupsQuery) -> AttributeGroupListReadModel:
        """Retrieve a paginated attribute group list.

        Args:
            query: Pagination parameters.

        Returns:
            Paginated list read model with items and total count.
        """
        count_result = await self._session.execute(_COUNT_ATTRIBUTE_GROUPS_SQL)
        total = count_result.scalar_one()

        result = await self._session.execute(
            _LIST_ATTRIBUTE_GROUPS_SQL,
            {"limit": query.limit, "offset": query.offset},
        )
        rows = result.mappings().all()

        items = [
            AttributeGroupReadModel(
                id=row["id"],
                code=row["code"],
                name_i18n=row["name_i18n"],
                sort_order=row["sort_order"],
            )
            for row in rows
        ]

        return AttributeGroupListReadModel(
            items=items,
            total=total,
            offset=query.offset,
            limit=query.limit,
        )
