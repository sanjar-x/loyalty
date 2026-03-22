"""
Query handler: paginated attribute group listing.

Strict CQRS read side -- does not use IUnitOfWork, domain aggregates, or
repositories. Queries the ORM directly via AsyncSession and returns a
Pydantic read model.
"""

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.application.queries.get_attribute_group import (
    attribute_group_orm_to_read_model,
)
from src.modules.catalog.application.queries.read_models import (
    AttributeGroupListReadModel,
    AttributeGroupReadModel,
)
from src.modules.catalog.infrastructure.models import (
    AttributeGroup as OrmAttributeGroup,
)


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
        count_result = await self._session.execute(
            select(func.count()).select_from(OrmAttributeGroup)
        )
        total = count_result.scalar_one()

        stmt = (
            select(OrmAttributeGroup)
            .order_by(OrmAttributeGroup.sort_order, OrmAttributeGroup.code)
            .limit(query.limit)
            .offset(query.offset)
        )
        result = await self._session.execute(stmt)
        rows = result.scalars().all()

        items = [attribute_group_orm_to_read_model(orm) for orm in rows]

        return AttributeGroupListReadModel(
            items=items,
            total=total,
            offset=query.offset,
            limit=query.limit,
        )
