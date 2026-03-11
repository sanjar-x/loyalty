# src/modules/catalog/infrastructure/repositories/category.py
import uuid

from sqlalchemy import Sequence, select

from src.modules.catalog.domain.interfaces import (
    ICategoryRepository,
)
from src.modules.catalog.infrastructure.models import (
    Category,
)
from src.modules.catalog.infrastructure.repositories.base import BaseRepository


class CategoryRepository(
    BaseRepository[Category], ICategoryRepository, model_class=Category
):
    async def get_all_ordered(self) -> Sequence[Category]:
        statement = select(self.model).order_by(
            self.model.level.asc(), self.model.sort_order.asc()
        )
        result = await self._session.execute(statement)
        return result.scalars().all()

    async def check_slug_exists(self, slug: str, parent_id: uuid.UUID | None) -> bool:
        statement = select(
            select(self.model)
            .where(self.model.slug == slug, self.model.parent_id == parent_id)
            .exists()
        )
        result = await self._session.execute(statement)
        return result.scalar()
