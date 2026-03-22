"""
Query handler: list all attribute bindings for a category.

CQRS read side -- queries ORM directly and returns read models.
"""

import uuid
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.application.queries.read_models import (
    CategoryAttributeBindingListReadModel,
    CategoryAttributeBindingReadModel,
)
from src.modules.catalog.infrastructure.models import (
    CategoryAttributeBinding as OrmBinding,
)


@dataclass(frozen=True)
class ListCategoryBindingsQuery:
    """Parameters for listing bindings of a category."""

    category_id: uuid.UUID
    offset: int = 0
    limit: int = 100


class ListCategoryBindingsHandler:
    """Fetch all attribute bindings for a given category."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def handle(
        self, query: ListCategoryBindingsQuery
    ) -> CategoryAttributeBindingListReadModel:
        """Retrieve a paginated list of bindings for a category."""
        base = select(OrmBinding).where(OrmBinding.category_id == query.category_id)

        count_stmt = select(func.count()).select_from(base.subquery())
        count_result = await self._session.execute(count_stmt)
        total: int = count_result.scalar_one()

        items_stmt = (
            base.order_by(OrmBinding.sort_order, OrmBinding.attribute_id)
            .offset(query.offset)
            .limit(query.limit)
        )
        result = await self._session.execute(items_stmt)
        rows = result.scalars().all()

        items = [
            CategoryAttributeBindingReadModel(
                id=orm.id,
                category_id=orm.category_id,
                attribute_id=orm.attribute_id,
                sort_order=orm.sort_order,
                requirement_level=orm.requirement_level.value,
                flag_overrides=dict(orm.flag_overrides) if orm.flag_overrides else None,
                filter_settings=dict(orm.filter_settings) if orm.filter_settings else None,
            )
            for orm in rows
        ]

        return CategoryAttributeBindingListReadModel(
            items=items,
            total=total,
            offset=query.offset,
            limit=query.limit,
        )
