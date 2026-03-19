"""
CategoryAttributeBinding repository -- Data Mapper implementation.

Translates between the domain ``CategoryAttributeBinding`` entity and the
``category_attribute_rules`` ORM table. Provides pair-uniqueness checks
and bulk sort/requirement updates.
"""

import uuid

from sqlalchemy import case, delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.domain.entities import (
    CategoryAttributeBinding as DomainBinding,
)
from src.modules.catalog.domain.interfaces import ICategoryAttributeBindingRepository
from src.modules.catalog.infrastructure.models import (
    CategoryAttributeRule as OrmRule,
)


class CategoryAttributeBindingRepository(ICategoryAttributeBindingRepository):
    """Data Mapper repository for CategoryAttributeBinding.

    Args:
        session: SQLAlchemy async session scoped to the current request.
    """

    def __init__(self, session: AsyncSession):
        self._session = session

    def _to_domain(self, orm: OrmRule) -> DomainBinding:
        """Map an ORM row to a domain entity."""
        return DomainBinding(
            id=orm.id,
            category_id=orm.category_id,
            attribute_id=orm.attribute_id,
            sort_order=orm.sort_order,
            requirement_level=orm.requirement_level,
            flag_overrides=dict(orm.flag_overrides) if orm.flag_overrides else None,
            filter_settings=dict(orm.filter_settings) if orm.filter_settings else None,
        )

    def _to_orm(self, domain: DomainBinding, orm: OrmRule | None = None) -> OrmRule:
        """Map a domain entity to an ORM row (create or update)."""
        if orm is None:
            orm = OrmRule()
        orm.id = domain.id
        orm.category_id = domain.category_id
        orm.attribute_id = domain.attribute_id
        orm.sort_order = domain.sort_order
        orm.requirement_level = domain.requirement_level
        orm.flag_overrides = domain.flag_overrides
        orm.filter_settings = domain.filter_settings
        return orm

    async def add(self, entity: DomainBinding) -> DomainBinding:
        """Persist a new binding and return the refreshed domain entity."""
        orm = self._to_orm(entity)
        self._session.add(orm)
        await self._session.flush()
        return self._to_domain(orm)

    async def get(self, binding_id: uuid.UUID) -> DomainBinding | None:
        """Retrieve a binding by primary key, or ``None``."""
        orm = await self._session.get(OrmRule, binding_id)
        if orm:
            return self._to_domain(orm)
        return None

    async def update(self, entity: DomainBinding) -> DomainBinding:
        """Merge updated domain state into the existing ORM row.

        Raises:
            ValueError: If the binding row does not exist.
        """
        orm = await self._session.get(OrmRule, entity.id)
        if not orm:
            raise ValueError(f"CategoryAttributeBinding with id {entity.id} not found in DB")
        orm = self._to_orm(entity, orm)
        await self._session.flush()
        return self._to_domain(orm)

    async def delete(self, binding_id: uuid.UUID) -> None:
        """Delete a binding row by primary key."""
        statement = delete(OrmRule).where(OrmRule.id == binding_id)
        await self._session.execute(statement)

    async def exists(self, category_id: uuid.UUID, attribute_id: uuid.UUID) -> bool:
        """Return ``True`` if a binding for this pair already exists."""
        statement = (
            select(OrmRule.id)
            .where(OrmRule.category_id == category_id, OrmRule.attribute_id == attribute_id)
            .limit(1)
        )
        result = await self._session.execute(statement)
        return result.first() is not None

    async def get_by_category_and_attribute(
        self, category_id: uuid.UUID, attribute_id: uuid.UUID
    ) -> DomainBinding | None:
        """Retrieve a binding by the category+attribute pair."""
        statement = (
            select(OrmRule)
            .where(OrmRule.category_id == category_id, OrmRule.attribute_id == attribute_id)
            .limit(1)
        )
        result = await self._session.execute(statement)
        orm = result.scalar_one_or_none()
        if orm:
            return self._to_domain(orm)
        return None

    async def bulk_update_sort_order(self, updates: list[tuple[uuid.UUID, int]]) -> None:
        """Bulk-update sort_order for multiple bindings in a single statement."""
        if not updates:
            return
        id_to_order = {bid: order for bid, order in updates}
        binding_ids = list(id_to_order.keys())
        stmt = (
            update(OrmRule)
            .where(OrmRule.id.in_(binding_ids))
            .values(
                sort_order=case(
                    *[(OrmRule.id == bid, order) for bid, order in id_to_order.items()],
                    else_=OrmRule.sort_order,
                )
            )
        )
        await self._session.execute(stmt)

    async def bulk_update_requirement_level(self, updates: list[tuple[uuid.UUID, str]]) -> None:
        """Bulk-update requirement_level for multiple bindings in a single statement."""
        if not updates:
            return
        id_to_level = {bid: level for bid, level in updates}
        binding_ids = list(id_to_level.keys())
        stmt = (
            update(OrmRule)
            .where(OrmRule.id.in_(binding_ids))
            .values(
                requirement_level=case(
                    *[(OrmRule.id == bid, level) for bid, level in id_to_level.items()],
                    else_=OrmRule.requirement_level,
                )
            )
        )
        await self._session.execute(stmt)
