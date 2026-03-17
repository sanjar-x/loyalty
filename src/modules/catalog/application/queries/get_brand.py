"""
Query Handler: получить бренд по ID.

Строгий CQRS — не использует IUnitOfWork, доменные агрегаты
и репозитории. Работает напрямую с AsyncSession + raw SQL,
возвращает Pydantic Read Model.
"""

import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.application.queries.read_models import BrandReadModel
from src.modules.catalog.domain.exceptions import BrandNotFoundError

_GET_BRAND_SQL = text(
    "SELECT id, name, slug, logo_url, logo_status FROM brands WHERE id = :brand_id"
)


class GetBrandHandler:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def handle(self, brand_id: uuid.UUID) -> BrandReadModel:
        result = await self._session.execute(_GET_BRAND_SQL, {"brand_id": brand_id})
        row = result.mappings().first()

        if row is None:
            raise BrandNotFoundError(brand_id=brand_id)

        return BrandReadModel(
            id=row["id"],
            name=row["name"],
            slug=row["slug"],
            logo_url=row["logo_url"],
            logo_status=row["logo_status"],
        )
