"""
AttributeValue repository -- Data Mapper implementation.

Translates between :class:`~src.modules.catalog.domain.entities.AttributeValue`
(domain) and the ``attribute_values`` ORM table. Provides code/slug uniqueness
checks scoped to the parent attribute and bulk sort-order updates.
"""

import uuid

from sqlalchemy import case, select, update

from src.modules.catalog.domain.entities import AttributeValue as DomainAttributeValue
from src.modules.catalog.domain.interfaces import IAttributeValueRepository
from src.modules.catalog.infrastructure.models import (
    AttributeValue as OrmAttributeValue,
)
from src.modules.catalog.infrastructure.models import (
    ProductAttributeValue as OrmProductAttributeValue,
)
from src.modules.catalog.infrastructure.repositories.base import BaseRepository


class AttributeValueRepository(
    BaseRepository[DomainAttributeValue, OrmAttributeValue],
    IAttributeValueRepository,
    model_class=OrmAttributeValue,
):
    """Data Mapper repository for AttributeValue child entities.

    Inherits generic CRUD from :class:`BaseRepository` and adds
    scoped uniqueness checks and bulk sort-order updates.
    """

    def _to_domain(self, orm: OrmAttributeValue) -> DomainAttributeValue:
        """Map an ORM row to a domain entity."""
        return DomainAttributeValue(
            id=orm.id,
            attribute_id=orm.attribute_id,
            code=orm.code,
            slug=orm.slug,
            value_i18n=dict(orm.value_i18n) if orm.value_i18n else {},
            search_aliases=list(orm.search_aliases) if orm.search_aliases else [],
            meta_data=dict(orm.meta_data) if orm.meta_data else {},
            value_group=orm.value_group,
            sort_order=orm.sort_order,
            is_active=orm.is_active,
        )

    def _to_orm(
        self, entity: DomainAttributeValue, orm: OrmAttributeValue | None = None
    ) -> OrmAttributeValue:
        """Map a domain entity to an ORM row (create or update)."""
        if orm is None:
            orm = OrmAttributeValue()
        orm.id = entity.id
        orm.attribute_id = entity.attribute_id
        orm.code = entity.code
        orm.slug = entity.slug
        orm.value_i18n = entity.value_i18n
        orm.search_aliases = entity.search_aliases
        orm.meta_data = entity.meta_data
        orm.value_group = entity.value_group
        orm.sort_order = entity.sort_order
        orm.is_active = entity.is_active
        return orm

    async def get_many(
        self, ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, DomainAttributeValue]:
        """Batch-load multiple attribute values by their UUIDs."""
        if not ids:
            return {}
        stmt = select(OrmAttributeValue).where(OrmAttributeValue.id.in_(ids))
        result = await self._session.execute(stmt)
        return {orm.id: self._to_domain(orm) for orm in result.scalars().all()}

    async def check_code_exists(self, attribute_id: uuid.UUID, code: str) -> bool:
        """Return ``True`` if the code is taken within this attribute."""
        stmt = (
            select(OrmAttributeValue.id)
            .where(
                OrmAttributeValue.attribute_id == attribute_id,
                OrmAttributeValue.code == code,
            )
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.first() is not None

    async def check_slug_exists(self, attribute_id: uuid.UUID, slug: str) -> bool:
        """Return ``True`` if the slug is taken within this attribute."""
        stmt = (
            select(OrmAttributeValue.id)
            .where(
                OrmAttributeValue.attribute_id == attribute_id,
                OrmAttributeValue.slug == slug,
            )
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.first() is not None

    async def has_product_references(self, value_id: uuid.UUID) -> bool:
        """Return ``True`` if any products reference this attribute value."""
        stmt = select(
            select(OrmProductAttributeValue.id)
            .where(OrmProductAttributeValue.attribute_value_id == value_id)
            .limit(1)
            .exists()
        )
        result = await self._session.execute(stmt)
        return bool(result.scalar())

    async def check_codes_exist(
        self, attribute_id: uuid.UUID, codes: list[str]
    ) -> set[str]:
        """Return the subset of codes that already exist for this attribute."""
        if not codes:
            return set()
        stmt = select(OrmAttributeValue.code).where(
            OrmAttributeValue.attribute_id == attribute_id,
            OrmAttributeValue.code.in_(codes),
        )
        result = await self._session.execute(stmt)
        return {row[0] for row in result.all()}

    async def check_slugs_exist(
        self, attribute_id: uuid.UUID, slugs: list[str]
    ) -> set[str]:
        """Return the subset of slugs that already exist for this attribute."""
        if not slugs:
            return set()
        stmt = select(OrmAttributeValue.slug).where(
            OrmAttributeValue.attribute_id == attribute_id,
            OrmAttributeValue.slug.in_(slugs),
        )
        result = await self._session.execute(stmt)
        return {row[0] for row in result.all()}

    async def list_ids_by_attribute(self, attribute_id: uuid.UUID) -> set[uuid.UUID]:
        """Return the set of value IDs belonging to the given attribute."""
        stmt = select(OrmAttributeValue.id).where(
            OrmAttributeValue.attribute_id == attribute_id
        )
        result = await self._session.execute(stmt)
        return {row[0] for row in result.all()}

    async def bulk_update_sort_order(
        self, updates: list[tuple[uuid.UUID, int]]
    ) -> None:
        """Bulk-update sort_order for multiple values in a single stmt."""
        if not updates:
            return

        # Build a CASE expression for efficient single-query bulk update
        id_to_order = {vid: order for vid, order in updates}
        value_ids = list(id_to_order.keys())

        stmt = (
            update(OrmAttributeValue)
            .where(OrmAttributeValue.id.in_(value_ids))
            .values(
                sort_order=case(
                    *[
                        (OrmAttributeValue.id == vid, order)
                        for vid, order in id_to_order.items()
                    ],
                    else_=OrmAttributeValue.sort_order,
                )
            )
        )
        await self._session.execute(stmt)
