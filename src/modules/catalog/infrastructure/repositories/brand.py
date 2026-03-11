# src/modules/catalog/infrastructure/repositories/catalog_repos.py
from sqlalchemy import select

from src.modules.catalog.domain.interfaces import (
    IBrandRepository,
)
from src.modules.catalog.infrastructure.models import (
    Brand,
)
from src.modules.catalog.infrastructure.repositories.base import BaseRepository


class BrandRepository(BaseRepository[Brand], IBrandRepository, model_class=Brand):
    async def get_by_slug(self, slug: str) -> Brand | None:
        statement = select(self.model).where(self.model.slug == slug)
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def check_slug_exists(self, slug: str) -> bool:
        statement = select(self.model).where(self.model.slug == slug).exists()
        result = await self._session.execute(statement)
        return result.scalar()
