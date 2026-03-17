"""
Query Handler: получить категорию по ID.

Строгий CQRS — не использует IUnitOfWork, доменные агрегаты
и репозитории. Работает напрямую с AsyncSession + raw SQL,
возвращает Pydantic Read Model.
"""

import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.application.queries.read_models import CategoryReadModel
from src.modules.catalog.domain.exceptions import CategoryNotFoundError

_GET_CATEGORY_SQL = text(
    "SELECT id, name, slug, full_slug, level, sort_order, parent_id "
    "FROM categories WHERE id = :category_id"
)


class GetCategoryHandler:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def handle(self, category_id: uuid.UUID) -> CategoryReadModel:
        result = await self._session.execute(_GET_CATEGORY_SQL, {"category_id": category_id})
        row = result.mappings().first()

        if row is None:
            raise CategoryNotFoundError(category_id=category_id)

        return CategoryReadModel(
            id=row["id"],
            name=row["name"],
            slug=row["slug"],
            full_slug=row["full_slug"],
            level=row["level"],
            sort_order=row["sort_order"],
            parent_id=row["parent_id"],
        )
