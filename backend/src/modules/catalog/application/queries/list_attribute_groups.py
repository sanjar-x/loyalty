"""
Query handler: paginated attribute group listing.

Strict CQRS read side — does not use IUnitOfWork, domain aggregates, or
repositories. Queries the ORM directly via AsyncSession and returns a
Pydantic read model.
"""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.application.queries.get_attribute_group import (
    attribute_group_orm_to_read_model,
)
from src.modules.catalog.application.queries.read_models import (
    AttributeGroupListReadModel,
)
from src.modules.catalog.infrastructure.models import (
    AttributeGroup as OrmAttributeGroup,
)
from src.shared.interfaces.logger import ILogger
from src.shared.pagination import paginate


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
    """Fetch a paginated list of attribute groups ordered by sort_order."""

    def __init__(self, session: AsyncSession, logger: ILogger):
        self._session = session
        self._logger = logger.bind(handler="ListAttributeGroupsHandler")

    async def handle(
        self, query: ListAttributeGroupsQuery
    ) -> AttributeGroupListReadModel:
        """Retrieve a paginated attribute group list.

        Args:
            query: Pagination parameters.

        Returns:
            Paginated list read model with items and total count.
        """
        base = select(OrmAttributeGroup).order_by(
            OrmAttributeGroup.sort_order, OrmAttributeGroup.code
        )

        items, total = await paginate(
            self._session,
            base,
            offset=query.offset,
            limit=query.limit,
            mapper=attribute_group_orm_to_read_model,
        )

        return AttributeGroupListReadModel(
            items=items,
            total=total,
            offset=query.offset,
            limit=query.limit,
        )
