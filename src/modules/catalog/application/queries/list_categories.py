"""
Query Handler: список категорий с пагинацией.

Строгий CQRS — не использует IUnitOfWork, доменные агрегаты
и репозитории. Работает напрямую с AsyncSession + raw SQL,
возвращает Pydantic Read Model.
"""

from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.application.queries.read_models import (
    CategoryListReadModel,
    CategoryReadModel,
)

_LIST_CATEGORIES_SQL = text(
    "SELECT id, name, slug, full_slug, level, sort_order, parent_id "
    "FROM categories "
    "ORDER BY level, sort_order, name "
    "LIMIT :limit OFFSET :offset"
)

_COUNT_CATEGORIES_SQL = text("SELECT count(*) FROM categories")


@dataclass(frozen=True)
class ListCategoriesQuery:
    offset: int = 0
    limit: int = 20


class ListCategoriesHandler:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def handle(self, query: ListCategoriesQuery) -> CategoryListReadModel:
        count_result = await self._session.execute(_COUNT_CATEGORIES_SQL)
        total: int = count_result.scalar_one()

        result = await self._session.execute(
            _LIST_CATEGORIES_SQL, {"limit": query.limit, "offset": query.offset}
        )
        rows = result.mappings().all()

        items = [
            CategoryReadModel(
                id=row["id"],
                name=row["name"],
                slug=row["slug"],
                full_slug=row["full_slug"],
                level=row["level"],
                sort_order=row["sort_order"],
                parent_id=row["parent_id"],
            )
            for row in rows
        ]

        return CategoryListReadModel(
            items=items,
            total=total,
            offset=query.offset,
            limit=query.limit,
        )
