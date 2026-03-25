"""
AttributeFamily repository -- Data Mapper implementation.

Translates between the domain ``AttributeFamily`` entity and the
``attribute_families`` ORM table. Provides tree traversal queries
using recursive CTEs for ancestor chain and descendant enumeration.
"""

import uuid

from sqlalchemy import select, text

from src.modules.catalog.domain.entities import AttributeFamily as DomainAttributeFamily
from src.modules.catalog.domain.interfaces import IAttributeFamilyRepository
from src.modules.catalog.infrastructure.models import (
    AttributeFamily as OrmAttributeFamily,
)
from src.modules.catalog.infrastructure.models import (
    Category as OrmCategory,
)
from src.modules.catalog.infrastructure.repositories.base import BaseRepository


class AttributeFamilyRepository(
    BaseRepository[DomainAttributeFamily, OrmAttributeFamily],
    IAttributeFamilyRepository,
    model_class=OrmAttributeFamily,
):
    """Data Mapper repository for AttributeFamily aggregate.

    Inherits generic CRUD from BaseRepository and adds
    tree traversal queries using WITH RECURSIVE CTEs.
    """

    def _to_domain(self, orm: OrmAttributeFamily) -> DomainAttributeFamily:
        return DomainAttributeFamily(
            id=orm.id,
            parent_id=orm.parent_id,
            code=orm.code,
            name_i18n=orm.name_i18n or {},
            description_i18n=orm.description_i18n or {},
            sort_order=orm.sort_order,
            level=orm.level,
        )

    def _to_orm(
        self, entity: DomainAttributeFamily, orm: OrmAttributeFamily | None = None
    ) -> OrmAttributeFamily:
        if orm is None:
            orm = OrmAttributeFamily()
        orm.id = entity.id
        orm.parent_id = entity.parent_id
        orm.code = entity.code
        orm.name_i18n = entity.name_i18n
        orm.description_i18n = entity.description_i18n
        orm.sort_order = entity.sort_order
        orm.level = entity.level
        return orm

    async def check_code_exists(self, code: str) -> bool:
        return await self._field_exists("code", code)

    async def check_code_exists_excluding(
        self, code: str, exclude_id: uuid.UUID
    ) -> bool:
        return await self._field_exists("code", code, exclude_id=exclude_id)

    async def has_children(self, family_id: uuid.UUID) -> bool:
        stmt = select(
            select(self.model.id)
            .where(self.model.parent_id == family_id)
            .limit(1)
            .exists()
        )
        result = await self._session.execute(stmt)
        return bool(result.scalar())

    async def has_category_references(self, family_id: uuid.UUID) -> bool:
        stmt = select(
            select(OrmCategory.id)
            .where(OrmCategory.family_id == family_id)
            .limit(1)
            .exists()
        )
        result = await self._session.execute(stmt)
        return bool(result.scalar())

    async def get_all_ordered(self) -> list[DomainAttributeFamily]:
        stmt = select(self.model).order_by(
            self.model.level.asc(), self.model.sort_order.asc()
        )
        result = await self._session.execute(stmt)
        return [self._to_domain(orm) for orm in result.scalars().all()]

    async def get_ancestor_chain(
        self, family_id: uuid.UUID
    ) -> list[DomainAttributeFamily]:
        """Return ancestor chain [root, ..., parent, self] using WITH RECURSIVE CTE."""
        cte_sql = text("""
            WITH RECURSIVE ancestors AS (
                SELECT id, parent_id, code, name_i18n, description_i18n,
                       sort_order, level, created_at, updated_at
                FROM attribute_families
                WHERE id = :family_id
                UNION ALL
                SELECT af.id, af.parent_id, af.code, af.name_i18n, af.description_i18n,
                       af.sort_order, af.level, af.created_at, af.updated_at
                FROM attribute_families af
                JOIN ancestors a ON a.parent_id = af.id
            )
            SELECT id, parent_id, code, name_i18n, description_i18n,
                   sort_order, level
            FROM ancestors
            ORDER BY level ASC
        """)
        result = await self._session.execute(cte_sql, {"family_id": family_id})
        rows = result.all()
        return [
            DomainAttributeFamily(
                id=row.id,
                parent_id=row.parent_id,
                code=row.code,
                name_i18n=row.name_i18n or {},
                description_i18n=row.description_i18n or {},
                sort_order=row.sort_order,
                level=row.level,
            )
            for row in rows
        ]

    async def get_descendant_ids(self, family_id: uuid.UUID) -> list[uuid.UUID]:
        """Return all descendant family IDs using WITH RECURSIVE CTE (excluding self)."""
        cte_sql = text("""
            WITH RECURSIVE descendants AS (
                SELECT id FROM attribute_families WHERE parent_id = :family_id
                UNION ALL
                SELECT af.id FROM attribute_families af
                JOIN descendants d ON af.parent_id = d.id
            )
            SELECT id FROM descendants
        """)
        result = await self._session.execute(cte_sql, {"family_id": family_id})
        return [row.id for row in result.all()]

    async def get_category_ids_by_family_ids(
        self, family_ids: list[uuid.UUID]
    ) -> list[uuid.UUID]:
        """Return category IDs that reference any of the given family IDs."""
        if not family_ids:
            return []
        stmt = select(OrmCategory.id).where(
            OrmCategory.effective_family_id.in_(family_ids)
        )
        result = await self._session.execute(stmt)
        return [row[0] for row in result.all()]
