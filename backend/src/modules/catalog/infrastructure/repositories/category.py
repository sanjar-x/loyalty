"""
Category repository — Data Mapper implementation.

Extends :class:`BaseRepository` with tree-specific operations such as
slug uniqueness within a parent, child existence checks, and bulk
``full_slug`` prefix updates for subtree renames.
"""

import uuid

from sqlalchemy import func, select, text, update

from src.modules.catalog.domain.entities import Category as DomainCategory
from src.modules.catalog.domain.interfaces import ICategoryRepository
from src.modules.catalog.infrastructure.models import Category as OrmCategory
from src.modules.catalog.infrastructure.models import Product as OrmProduct
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
            name_i18n=orm.name_i18n or {},
            slug=orm.slug,
            full_slug=orm.full_slug,
            level=orm.level,
            sort_order=orm.sort_order,
            family_id=orm.family_id,
            effective_family_id=orm.effective_family_id,
        )

    def _to_orm(
        self, entity: DomainCategory, orm: OrmCategory | None = None
    ) -> OrmCategory:
        """Map a domain Category entity to an ORM row (create or update)."""
        if orm is None:
            orm = OrmCategory()
        orm.id = entity.id
        orm.parent_id = entity.parent_id
        orm.name_i18n = entity.name_i18n
        orm.slug = entity.slug
        orm.full_slug = entity.full_slug
        orm.level = entity.level
        orm.sort_order = entity.sort_order
        orm.family_id = entity.family_id
        orm.effective_family_id = entity.effective_family_id
        return orm

    async def get_all_ordered(self) -> list[DomainCategory]:
        """Return all categories ordered by level then sort_order."""
        stmt = select(self.model).order_by(
            self.model.level.asc(), self.model.sort_order.asc()
        )
        result = await self._session.execute(stmt)
        orms = result.scalars().all()
        return [self._to_domain(orm) for orm in orms]

    async def check_slug_exists(self, slug: str, parent_id: uuid.UUID | None) -> bool:
        """Return ``True`` if a sibling with this slug already exists."""
        return await self._field_exists(
            "slug", slug, extra_filters=[self.model.parent_id == parent_id]
        )

    # get_for_update is inherited from BaseRepository

    async def check_slug_exists_excluding(
        self, slug: str, parent_id: uuid.UUID | None, exclude_id: uuid.UUID
    ) -> bool:
        """Return ``True`` if the slug is taken by a sibling other than *exclude_id*."""
        return await self._field_exists(
            "slug",
            slug,
            exclude_id=exclude_id,
            extra_filters=[self.model.parent_id == parent_id],
        )

    async def has_children(self, category_id: uuid.UUID) -> bool:
        """Return ``True`` if the category has at least one child."""
        stmt = select(
            select(self.model.id)
            .where(self.model.parent_id == category_id)
            .limit(1)
            .exists()
        )
        result = await self._session.execute(stmt)
        return bool(result.scalar())

    async def has_products(self, category_id: uuid.UUID) -> bool:
        """Return ``True`` if any non-deleted product references this category."""
        stmt = select(
            select(OrmProduct.id)
            .where(
                OrmProduct.primary_category_id == category_id,
                OrmProduct.deleted_at.is_(None),
            )
            .limit(1)
            .exists()
        )
        result = await self._session.execute(stmt)
        return bool(result.scalar())

    async def update_descendants_full_slug(
        self, old_prefix: str, new_prefix: str
    ) -> None:
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

    async def propagate_effective_family_id(
        self, category_id: uuid.UUID, effective_family_id: uuid.UUID | None
    ) -> list[uuid.UUID]:
        """Propagate effective_family_id to inheriting descendants via recursive CTE."""
        cte_sql = text("""
            WITH RECURSIVE subtree AS (
                SELECT id
                FROM categories
                WHERE parent_id = :root_id AND family_id IS NULL
                UNION ALL
                SELECT c.id
                FROM categories c
                JOIN subtree s ON c.parent_id = s.id
                WHERE c.family_id IS NULL
            )
            UPDATE categories
            SET effective_family_id = :eff_fid
            WHERE id IN (SELECT id FROM subtree)
            RETURNING id
        """)
        result = await self._session.execute(
            cte_sql,
            {
                "root_id": category_id,
                "eff_fid": effective_family_id,
            },
        )
        return [row[0] for row in result.all()]
