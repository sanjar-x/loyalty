"""
Category repository — Data Mapper implementation.

Extends :class:`BaseRepository` with tree-specific operations such as
slug uniqueness within a parent, child existence checks, and bulk
``full_slug`` prefix updates for subtree renames.
"""

import uuid

from sqlalchemy import func, select, update

from src.modules.catalog.domain.entities import Category as DomainCategory
from src.modules.catalog.domain.interfaces import ICategoryRepository
from src.modules.catalog.infrastructure.models import Category as OrmCategory
from src.modules.catalog.infrastructure.repositories.base import BaseRepository


class CategoryRepository(
    BaseRepository[DomainCategory, OrmCategory],
    ICategoryRepository,
    model_class=OrmCategory,
):
    """Data Mapper repository for the Category aggregate.

    Inherits generic CRUD from :class:`BaseRepository` and adds
    category-tree-aware queries required by the domain interfaces.
    """

    def _to_domain(self, orm: OrmCategory) -> DomainCategory:
        """Map an ORM Category row to a domain Category entity."""
        return DomainCategory(
            id=orm.id,
            parent_id=orm.parent_id,
            name=orm.name,
            slug=orm.slug,
            full_slug=orm.full_slug,
            level=orm.level,
            sort_order=orm.sort_order,
        )

    def _to_orm(self, entity: DomainCategory, orm: OrmCategory | None = None) -> OrmCategory:
        """Map a domain Category entity to an ORM row (create or update)."""
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
        """Return all categories ordered by level then sort_order."""
        stmt = select(self.model).order_by(self.model.level.asc(), self.model.sort_order.asc())
        result = await self._session.execute(stmt)
        orms = result.scalars().all()
        return [self._to_domain(orm) for orm in orms]

    async def check_slug_exists(self, slug: str, parent_id: uuid.UUID | None) -> bool:
        """Return ``True`` if a sibling with this slug already exists."""
        stmt = select(
            select(self.model)
            .where(self.model.slug == slug, self.model.parent_id == parent_id)
            .exists()
        )
        result = await self._session.execute(stmt)
        return bool(result.scalar())

    async def get_for_update(self, category_id: uuid.UUID) -> DomainCategory | None:
        """Retrieve a category with a ``SELECT … FOR UPDATE`` row lock."""
        stmt = select(self.model).where(self.model.id == category_id).with_for_update()
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    async def check_slug_exists_excluding(
        self, slug: str, parent_id: uuid.UUID | None, exclude_id: uuid.UUID
    ) -> bool:
        """Return ``True`` if the slug is taken by a sibling other than *exclude_id*."""
        stmt = select(
            select(self.model)
            .where(
                self.model.slug == slug,
                self.model.parent_id == parent_id,
                self.model.id != exclude_id,
            )
            .exists()
        )
        result = await self._session.execute(stmt)
        return bool(result.scalar())

    async def has_children(self, category_id: uuid.UUID) -> bool:
        """Return ``True`` if the category has at least one child."""
        stmt = select(
            select(self.model.id).where(self.model.parent_id == category_id).limit(1).exists()
        )
        result = await self._session.execute(stmt)
        return bool(result.scalar())

    async def update_descendants_full_slug(self, old_prefix: str, new_prefix: str) -> None:
        """Bulk-rename the ``full_slug`` prefix for all descendant categories.

        Executes a single ``UPDATE … SET full_slug = concat(...)`` to
        efficiently propagate a parent slug change down the subtree.
        """
        stmt = (
            update(self.model)
            .where(self.model.full_slug.like(f"{old_prefix}/%"))
            .values(
                full_slug=func.concat(
                    new_prefix,
                    func.substr(self.model.full_slug, len(old_prefix) + 1),
                )
            )
        )
        await self._session.execute(stmt)
