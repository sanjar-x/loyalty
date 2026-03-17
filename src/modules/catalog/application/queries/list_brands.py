"""
Query Handler: список брендов с пагинацией.

Строгий CQRS — не использует IUnitOfWork, доменные агрегаты
и репозитории. Работает напрямую с AsyncSession + raw SQL,
возвращает Pydantic Read Model.
"""

from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.application.queries.read_models import (
    BrandListReadModel,
    BrandReadModel,
)

_LIST_BRANDS_SQL = text(
    "SELECT id, name, slug, logo_url, logo_status "
    "FROM brands "
    "ORDER BY name "
    "LIMIT :limit OFFSET :offset"
)

_COUNT_BRANDS_SQL = text("SELECT count(*) FROM brands")


@dataclass(frozen=True)
class ListBrandsQuery:
    offset: int = 0
    limit: int = 20


class ListBrandsHandler:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def handle(self, query: ListBrandsQuery) -> BrandListReadModel:
        count_result = await self._session.execute(_COUNT_BRANDS_SQL)
        total = count_result.scalar_one()

        result = await self._session.execute(
            _LIST_BRANDS_SQL, {"limit": query.limit, "offset": query.offset}
        )
        rows = result.mappings().all()

        items = [
            BrandReadModel(
                id=row["id"],
                name=row["name"],
                slug=row["slug"],
                logo_url=row["logo_url"],
                logo_status=row["logo_status"],
            )
            for row in rows
        ]

        return BrandListReadModel(
            items=items,
            total=total,
            offset=query.offset,
            limit=query.limit,
        )
