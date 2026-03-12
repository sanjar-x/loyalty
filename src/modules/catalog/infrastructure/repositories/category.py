# src/modules/catalog/infrastructure/repositories/category.py
import uuid

from sqlalchemy import select

from src.modules.catalog.domain.entities import Category as DomainCategory
from src.modules.catalog.domain.interfaces import ICategoryRepository
from src.modules.catalog.infrastructure.models import Category as OrmCategory
from src.modules.catalog.infrastructure.repositories.base import BaseRepository


class CategoryRepository(
    BaseRepository[DomainCategory, OrmCategory],
    ICategoryRepository,
    model_class=OrmCategory,
):
    def _to_domain(self, orm: OrmCategory) -> DomainCategory:
        return DomainCategory(
            id=orm.id,
            parent_id=orm.parent_id,
            name=orm.name,
            slug=orm.slug,
            full_slug=orm.full_slug,
            level=orm.level,
            sort_order=orm.sort_order,
        )

    def _to_orm(
        self, entity: DomainCategory, orm: OrmCategory | None = None
    ) -> OrmCategory:
        if orm is None:
            orm = OrmCategory()
        orm.id = entity.id
        orm.parent_id = entity.parent_id
        orm.name = entity.name
        orm.slug = entity.slug
        orm.full_slug = entity.full_slug
        orm.level = entity.level
        orm.sort_order = entity.sort_order
        return orm

    async def get_all_ordered(self) -> list[DomainCategory]:
        statement = select(self.model).order_by(
            self.model.level.asc(), self.model.sort_order.asc()
        )
        result = await self._session.execute(statement)
        orms = result.scalars().all()
        return [self._to_domain(orm) for orm in orms]

    async def check_slug_exists(self, slug: str, parent_id: uuid.UUID | None) -> bool:
        statement = select(
            select(self.model)
            .where(self.model.slug == slug, self.model.parent_id == parent_id)
            .exists()
        )
        result = await self._session.execute(statement)
        return result.scalar()
