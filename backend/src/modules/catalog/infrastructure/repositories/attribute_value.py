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
        """Map an ORM row to a domain entity.

        Note: ORM ``group_code`` is mapped to domain ``value_group``.
        The domain uses ``value_group`` (a UI grouping label), while the
        database column is ``group_code``. This is a deliberate rename.
        """
        return DomainAttributeValue(
            id=orm.id,
            attribute_id=orm.attribute_id,
            code=orm.code,
            slug=orm.slug,
            value_i18n=dict(orm.value_i18n) if orm.value_i18n else {},
            search_aliases=list(orm.search_aliases) if orm.search_aliases else [],
            meta_data=dict(orm.meta_data) if orm.meta_data else {},
            value_group=orm.group_code,  # ORM group_code -> domain value_group
            sort_order=orm.sort_order,
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
        orm.group_code = entity.value_group  # domain value_group -> ORM group_code
        orm.sort_order = entity.sort_order
        return orm

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

    async def check_code_exists_excluding(
        self, attribute_id: uuid.UUID, code: str, exclude_id: uuid.UUID
    ) -> bool:
        """Return ``True`` if the code is taken by another value within this attribute."""
        stmt = (
            select(OrmAttributeValue.id)
            .where(
                OrmAttributeValue.attribute_id == attribute_id,
                OrmAttributeValue.code == code,
                OrmAttributeValue.id != exclude_id,
            )
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.first() is not None

    async def check_slug_exists_excluding(
        self, attribute_id: uuid.UUID, slug: str, exclude_id: uuid.UUID
    ) -> bool:
        """Return ``True`` if the slug is taken by another value within this attribute."""
        stmt = (
            select(OrmAttributeValue.id)
            .where(
                OrmAttributeValue.attribute_id == attribute_id,
                OrmAttributeValue.slug == slug,
                OrmAttributeValue.id != exclude_id,
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

    async def list_ids_by_attribute(self, attribute_id: uuid.UUID) -> set[uuid.UUID]:
        """Return the set of value IDs belonging to the given attribute."""
        stmt = select(OrmAttributeValue.id).where(OrmAttributeValue.attribute_id == attribute_id)
        result = await self._session.execute(stmt)
        return {row[0] for row in result.all()}

    async def bulk_update_sort_order(self, updates: list[tuple[uuid.UUID, int]]) -> None:
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
                    *[(OrmAttributeValue.id == vid, order) for vid, order in id_to_order.items()],
                    else_=OrmAttributeValue.sort_order,
                )
            )
        )
        await self._session.execute(stmt)
