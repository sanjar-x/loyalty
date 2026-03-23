"""
Query handler: paginated category listing.

Strict CQRS read side — does not use IUnitOfWork, domain aggregates, or
repositories. Queries the ORM directly via AsyncSession and returns a
Pydantic read model.
"""

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.application.queries.get_category import category_orm_to_read_model
from src.modules.catalog.application.queries.read_models import (
    CategoryListReadModel,
    CategoryReadModel,
)
from src.modules.catalog.infrastructure.models import Category as OrmCategory
from src.shared.interfaces.logger import ILogger


@dataclass(frozen=True)
class ListCategoriesQuery:
    """Pagination parameters for category listing.

    Attributes:
        offset: Number of records to skip.
        limit: Maximum number of records to return.
    """

    offset: int = 0
    limit: int = 20


class ListCategoriesHandler:
    """Fetch a paginated list of categories."""

    def __init__(self, session: AsyncSession, logger: ILogger):
        self._session = session
        self._logger = logger.bind(handler="ListCategoriesHandler")

    async def handle(self, query: ListCategoriesQuery) -> CategoryListReadModel:
        """Retrieve a paginated category list.

        Args:
            query: Pagination parameters.

        Returns:
            Paginated list read model with items and total count.
        """
        count_result = await self._session.execute(select(func.count()).select_from(OrmCategory))
        total: int = count_result.scalar_one()

        stmt = (
            select(OrmCategory)
            .order_by(OrmCategory.level, OrmCategory.sort_order, OrmCategory.name)
            .limit(query.limit)
            .offset(query.offset)
        )
        result = await self._session.execute(stmt)
        rows = result.scalars().all()

        items = [category_orm_to_read_model(orm) for orm in rows]

        return CategoryListReadModel(
            items=items,
            total=total,
            offset=query.offset,
            limit=query.limit,
        )
