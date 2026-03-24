"""
FamilyAttributeBinding repository -- Data Mapper implementation.

Translates between the domain ``FamilyAttributeBinding`` entity and the
``family_attribute_bindings`` ORM table. Provides pair-uniqueness checks,
batch loading, and bulk sort updates.
"""

import uuid
from collections import defaultdict

from sqlalchemy import case, select, update

from src.modules.catalog.domain.entities import (
    FamilyAttributeBinding as DomainBinding,
)
from src.modules.catalog.domain.interfaces import IFamilyAttributeBindingRepository
from src.modules.catalog.infrastructure.models import (
    FamilyAttributeBinding as OrmBinding,
)
from src.modules.catalog.infrastructure.repositories.base import BaseRepository


class FamilyAttributeBindingRepository(
    BaseRepository[DomainBinding, OrmBinding],
    IFamilyAttributeBindingRepository,
    model_class=OrmBinding,
):
    """Data Mapper repository for FamilyAttributeBinding.

    Inherits generic CRUD from :class:`BaseRepository` and adds
    pair-uniqueness checks, batch loading, and bulk update operations.
    """

    def _to_domain(self, orm: OrmBinding) -> DomainBinding:
        """Map an ORM row to a domain entity."""
        return DomainBinding(
            id=orm.id,
            family_id=orm.family_id,
            attribute_id=orm.attribute_id,
            sort_order=orm.sort_order,
            requirement_level=orm.requirement_level,
            flag_overrides=dict(orm.flag_overrides) if orm.flag_overrides else None,
            filter_settings=dict(orm.filter_settings) if orm.filter_settings else None,
        )

    def _to_orm(
        self, entity: DomainBinding, orm: OrmBinding | None = None
    ) -> OrmBinding:
        """Map a domain entity to an ORM row (create or update)."""
        if orm is None:
            orm = OrmBinding()
        orm.id = entity.id
        orm.family_id = entity.family_id
        orm.attribute_id = entity.attribute_id
        orm.sort_order = entity.sort_order
        orm.requirement_level = entity.requirement_level
        orm.flag_overrides = entity.flag_overrides
        orm.filter_settings = entity.filter_settings
        return orm

    async def check_binding_exists(
        self, family_id: uuid.UUID, attribute_id: uuid.UUID
    ) -> bool:
        """Return ``True`` if a binding for this pair already exists."""
        stmt = (
            select(OrmBinding.id)
            .where(
                OrmBinding.family_id == family_id,
                OrmBinding.attribute_id == attribute_id,
            )
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.first() is not None

    async def get_by_family_and_attribute(
        self, family_id: uuid.UUID, attribute_id: uuid.UUID
    ) -> DomainBinding | None:
        """Retrieve a binding by the family+attribute pair."""
        stmt = (
            select(OrmBinding)
            .where(
                OrmBinding.family_id == family_id,
                OrmBinding.attribute_id == attribute_id,
            )
            .limit(1)
        )
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        if orm:
            return self._to_domain(orm)
        return None

    async def list_ids_by_family(self, family_id: uuid.UUID) -> set[uuid.UUID]:
        """Return the set of binding IDs belonging to the given family."""
        stmt = select(OrmBinding.id).where(OrmBinding.family_id == family_id)
        result = await self._session.execute(stmt)
        return {row[0] for row in result.all()}

    async def get_bindings_for_families(
        self, family_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, list[DomainBinding]]:
        """Batch-load all bindings for a list of family IDs.

        Returns dict mapping family_id -> list of domain bindings, ordered by sort_order.
        """
        if not family_ids:
            return {}
        stmt = (
            select(OrmBinding)
            .where(OrmBinding.family_id.in_(family_ids))
            .order_by(OrmBinding.sort_order)
        )
        result = await self._session.execute(stmt)
        bindings_map: dict[uuid.UUID, list[DomainBinding]] = defaultdict(list)
        for orm in result.scalars().all():
            bindings_map[orm.family_id].append(self._to_domain(orm))
        return dict(bindings_map)

    async def bulk_update_sort_order(
        self, updates: list[tuple[uuid.UUID, int]]
    ) -> None:
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
                    *[
                        (OrmBinding.id == bid, order)
                        for bid, order in id_to_order.items()
                    ],
                    else_=OrmBinding.sort_order,
                )
            )
        )
        await self._session.execute(stmt)

    async def has_bindings_for_attribute(self, attribute_id: uuid.UUID) -> bool:
        """Check whether any family binds this attribute (for deletion guard)."""
        stmt = (
            select(OrmBinding.id)
            .where(OrmBinding.attribute_id == attribute_id)
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.first() is not None
