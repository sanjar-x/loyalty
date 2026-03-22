"""
CategoryAttributeBinding repository -- Data Mapper implementation.

Translates between the domain ``CategoryAttributeBinding`` entity and the
``category_attribute_rules`` ORM table. Provides pair-uniqueness checks
and bulk sort/requirement updates.
"""

import uuid

from sqlalchemy import case, select, update

from src.modules.catalog.domain.entities import (
    CategoryAttributeBinding as DomainBinding,
)
from src.modules.catalog.domain.interfaces import ICategoryAttributeBindingRepository
from src.modules.catalog.infrastructure.models import (
    CategoryAttributeBinding as OrmBinding,
)
from src.modules.catalog.infrastructure.repositories.base import BaseRepository


class CategoryAttributeBindingRepository(
    BaseRepository[DomainBinding, OrmBinding],
    ICategoryAttributeBindingRepository,
    model_class=OrmBinding,
):
    """Data Mapper repository for CategoryAttributeBinding.

    Inherits generic CRUD from :class:`BaseRepository` and adds
    pair-uniqueness checks and bulk update operations.
    """

    def _to_domain(self, orm: OrmBinding) -> DomainBinding:
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

    def _to_orm(self, entity: DomainBinding, orm: OrmBinding | None = None) -> OrmBinding:
        """Map a domain entity to an ORM row (create or update)."""
        if orm is None:
            orm = OrmBinding()
        orm.id = entity.id
        orm.category_id = entity.category_id
        orm.attribute_id = entity.attribute_id
        orm.sort_order = entity.sort_order
        orm.requirement_level = entity.requirement_level
        orm.flag_overrides = entity.flag_overrides
        orm.filter_settings = entity.filter_settings
        return orm

    async def exists(self, category_id: uuid.UUID, attribute_id: uuid.UUID) -> bool:
        """Return ``True`` if a binding for this pair already exists."""
        stmt = (
            select(OrmBinding.id)
            .where(OrmBinding.category_id == category_id, OrmBinding.attribute_id == attribute_id)
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.first() is not None

    async def get_by_category_and_attribute(
        self, category_id: uuid.UUID, attribute_id: uuid.UUID
    ) -> DomainBinding | None:
        """Retrieve a binding by the category+attribute pair."""
        stmt = (
            select(OrmBinding)
            .where(OrmBinding.category_id == category_id, OrmBinding.attribute_id == attribute_id)
            .limit(1)
        )
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        if orm:
            return self._to_domain(orm)
        return None

    async def bulk_update_sort_order(self, updates: list[tuple[uuid.UUID, int]]) -> None:
        """Bulk-update sort_order for multiple bindings in a single stmt."""
        if not updates:
            return
        id_to_order = {bid: order for bid, order in updates}
        binding_ids = list(id_to_order.keys())
        stmt = (
            update(OrmBinding)
            .where(OrmBinding.id.in_(binding_ids))
            .values(
                sort_order=case(
                    *[(OrmBinding.id == bid, order) for bid, order in id_to_order.items()],
                    else_=OrmBinding.sort_order,
                )
            )
        )
        await self._session.execute(stmt)

    async def bulk_update_requirement_level(self, updates: list[tuple[uuid.UUID, str]]) -> None:
        """Bulk-update requirement_level for multiple bindings in a single stmt."""
        if not updates:
            return
        id_to_level = {bid: level for bid, level in updates}
        binding_ids = list(id_to_level.keys())
        stmt = (
            update(OrmBinding)
            .where(OrmBinding.id.in_(binding_ids))
            .values(
                requirement_level=case(
                    *[(OrmBinding.id == bid, level) for bid, level in id_to_level.items()],
                    else_=OrmBinding.requirement_level,
                )
            )
        )
        await self._session.execute(stmt)
