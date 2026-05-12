"""
TemplateAttributeBinding repository -- Data Mapper implementation.

Translates between the domain ``TemplateAttributeBinding`` entity and the
``template_attribute_bindings`` ORM table. Provides pair-uniqueness checks,
batch loading, and bulk sort updates.
"""

import uuid
from collections import defaultdict

from sqlalchemy import case, select, update
from sqlalchemy.exc import IntegrityError

from src.modules.catalog.domain.entities import (
    TemplateAttributeBinding as DomainBinding,
)
from src.modules.catalog.domain.exceptions import (
    TemplateAttributeBindingAlreadyExistsError,
)
from src.modules.catalog.domain.interfaces import ITemplateAttributeBindingRepository
from src.modules.catalog.infrastructure.models import (
    TemplateAttributeBinding as OrmBinding,
)
from src.modules.catalog.infrastructure.repositories.base import BaseRepository


class TemplateAttributeBindingRepository(
    BaseRepository[DomainBinding, OrmBinding],
    ITemplateAttributeBindingRepository,
    model_class=OrmBinding,
):
    """Data Mapper repository for TemplateAttributeBinding.

    Inherits generic CRUD from :class:`BaseRepository` and adds
    pair-uniqueness checks, batch loading, and bulk update operations.
    """

    def _to_domain(self, orm: OrmBinding) -> DomainBinding:
        """Map an ORM row to a domain entity."""
        return DomainBinding(
            id=orm.id,
            template_id=orm.template_id,
            attribute_id=orm.attribute_id,
            sort_order=orm.sort_order,
            requirement_level=orm.requirement_level,
            filter_settings=dict(orm.filter_settings) if orm.filter_settings else None,
        )

    def _to_orm(
        self, entity: DomainBinding, orm: OrmBinding | None = None
    ) -> OrmBinding:
        """Map a domain entity to an ORM row (create or update)."""
        if orm is None:
            orm = OrmBinding()
        orm.id = entity.id
        orm.template_id = entity.template_id
        orm.attribute_id = entity.attribute_id
        orm.sort_order = entity.sort_order
        orm.requirement_level = entity.requirement_level
        orm.filter_settings = entity.filter_settings
        return orm

    async def add(self, entity: DomainBinding) -> DomainBinding:
        """Persist a new template-attribute binding and return the refreshed copy."""
        orm = self._to_orm(entity)
        self._session.add(orm)
        try:
            await self._session.flush()
        except IntegrityError as e:
            constraint = str(e.orig) if e.orig else str(e)
            if "uix_template_attr_binding" in constraint:
                raise TemplateAttributeBindingAlreadyExistsError(
                    template_id=entity.template_id, attribute_id=entity.attribute_id
                ) from e
            raise
        return self._to_domain(orm)

    async def check_binding_exists(
        self, template_id: uuid.UUID, attribute_id: uuid.UUID
    ) -> bool:
        """Return ``True`` if a binding for this pair already exists."""
        stmt = (
            select(OrmBinding.id)
            .where(
                OrmBinding.template_id == template_id,
                OrmBinding.attribute_id == attribute_id,
            )
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.first() is not None

    async def list_ids_by_template(self, template_id: uuid.UUID) -> set[uuid.UUID]:
        """Return the set of binding IDs belonging to the given template."""
        stmt = select(OrmBinding.id).where(OrmBinding.template_id == template_id)
        result = await self._session.execute(stmt)
        return {row[0] for row in result.all()}

    async def get_bindings_for_templates(
        self, template_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, list[DomainBinding]]:
        """Batch-load all bindings for a list of template IDs.

        Returns dict mapping template_id -> list of domain bindings, ordered by sort_order.
        """
        if not template_ids:
            return {}
        stmt = (
            select(OrmBinding)
            .where(OrmBinding.template_id.in_(template_ids))
            .order_by(OrmBinding.sort_order)
        )
        result = await self._session.execute(stmt)
        bindings_map: dict[uuid.UUID, list[DomainBinding]] = defaultdict(list)
        for orm in result.scalars().all():
            bindings_map[orm.template_id].append(self._to_domain(orm))
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
        """Check whether any template binds this attribute (for deletion guard)."""
        stmt = (
            select(OrmBinding.id)
            .where(OrmBinding.attribute_id == attribute_id)
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.first() is not None

    async def get_template_ids_for_attribute(
        self, attribute_id: uuid.UUID
    ) -> list[uuid.UUID]:
        """Return template IDs that bind the given attribute."""
        stmt = (
            select(OrmBinding.template_id)
            .where(OrmBinding.attribute_id == attribute_id)
            .distinct()
        )
        result = await self._session.execute(stmt)
        return [row[0] for row in result.all()]
