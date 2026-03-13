# src/modules/catalog/infrastructure/queries.py
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.infrastructure.models import Category

from .dto import CategoryTreeNodeDTO  # Импортируем созданный DTO


class SqlCategoryQueryService:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def fetch_all_for_tree(self) -> list[CategoryTreeNodeDTO]:
        stmt = select(
            Category.id,
            Category.name,
            Category.slug,
            Category.full_slug,
            Category.level,
            Category.sort_order,
            Category.parent_id,
        ).order_by(Category.level, Category.sort_order)

        result = await self._session.execute(stmt)
        return [
            CategoryTreeNodeDTO(
                id=row.id,
                name=row.name,
                slug=row.slug,
                full_slug=row.full_slug,
                level=row.level,
                sort_order=row.sort_order,
                parent_id=row.parent_id,
                children=[],
            )
            for row in result.mappings().all()
        ]
