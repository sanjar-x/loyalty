"""
AttributeValue repository -- Data Mapper implementation.

Translates between :class:`~src.modules.catalog.domain.entities.AttributeValue`
(domain) and the ``attribute_values`` ORM table. Provides code/slug uniqueness
checks scoped to the parent attribute and bulk sort-order updates.
"""

import uuid

from sqlalchemy import case, delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.domain.entities import AttributeValue as DomainAttributeValue
from src.modules.catalog.domain.interfaces import IAttributeValueRepository
from src.modules.catalog.infrastructure.models import (
    AttributeValue as OrmAttributeValue,
)


class AttributeValueRepository(IAttributeValueRepository):
    """Data Mapper repository for AttributeValue child entities.

    Args:
        session: SQLAlchemy async session scoped to the current request.
    """

    def __init__(self, session: AsyncSession):
        self._session = session

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
            value_group=orm.group_code,
            sort_order=orm.sort_order,
        )

    def _to_orm(
        self, domain: DomainAttributeValue, orm: OrmAttributeValue | None = None
    ) -> OrmAttributeValue:
        """Map a domain entity to an ORM row (create or update)."""
        if orm is None:
            orm = OrmAttributeValue()
        orm.id = domain.id
        orm.attribute_id = domain.attribute_id
        orm.code = domain.code
        orm.slug = domain.slug
        orm.value_i18n = domain.value_i18n
        orm.search_aliases = domain.search_aliases
        orm.meta_data = domain.meta_data
        orm.group_code = domain.value_group
        orm.sort_order = domain.sort_order
        return orm

    async def add(self, entity: DomainAttributeValue) -> DomainAttributeValue:
        """Persist a new attribute value and return the refreshed domain entity."""
        orm = self._to_orm(entity)
        self._session.add(orm)
        await self._session.flush()
        return self._to_domain(orm)

    async def get(self, value_id: uuid.UUID) -> DomainAttributeValue | None:
        """Retrieve an attribute value by primary key, or ``None``."""
        orm = await self._session.get(OrmAttributeValue, value_id)
        if orm:
            return self._to_domain(orm)
        return None

    async def update(self, entity: DomainAttributeValue) -> DomainAttributeValue:
        """Merge updated domain state into the existing ORM row.

        Raises:
            ValueError: If the value row does not exist.
        """
        orm = await self._session.get(OrmAttributeValue, entity.id)
        if not orm:
            raise ValueError(f"AttributeValue with id {entity.id} not found in DB")
        orm = self._to_orm(entity, orm)
        await self._session.flush()
        return self._to_domain(orm)

    async def delete(self, value_id: uuid.UUID) -> None:
        """Delete an attribute value row by primary key."""
        statement = delete(OrmAttributeValue).where(OrmAttributeValue.id == value_id)
        await self._session.execute(statement)

    async def check_code_exists(self, attribute_id: uuid.UUID, code: str) -> bool:
        """Return ``True`` if the code is taken within this attribute."""
        statement = (
            select(OrmAttributeValue.id)
            .where(
                OrmAttributeValue.attribute_id == attribute_id,
                OrmAttributeValue.code == code,
            )
            .limit(1)
        )
        result = await self._session.execute(statement)
        return result.first() is not None

    async def check_slug_exists(self, attribute_id: uuid.UUID, slug: str) -> bool:
        """Return ``True`` if the slug is taken within this attribute."""
        statement = (
            select(OrmAttributeValue.id)
            .where(
                OrmAttributeValue.attribute_id == attribute_id,
                OrmAttributeValue.slug == slug,
            )
            .limit(1)
        )
        result = await self._session.execute(statement)
        return result.first() is not None

    async def check_code_exists_excluding(
        self, attribute_id: uuid.UUID, code: str, exclude_id: uuid.UUID
    ) -> bool:
        """Return ``True`` if the code is taken by another value within this attribute."""
        statement = (
            select(OrmAttributeValue.id)
            .where(
                OrmAttributeValue.attribute_id == attribute_id,
                OrmAttributeValue.code == code,
                OrmAttributeValue.id != exclude_id,
            )
            .limit(1)
        )
        result = await self._session.execute(statement)
        return result.first() is not None

    async def check_slug_exists_excluding(
        self, attribute_id: uuid.UUID, slug: str, exclude_id: uuid.UUID
    ) -> bool:
        """Return ``True`` if the slug is taken by another value within this attribute."""
        statement = (
            select(OrmAttributeValue.id)
            .where(
                OrmAttributeValue.attribute_id == attribute_id,
                OrmAttributeValue.slug == slug,
                OrmAttributeValue.id != exclude_id,
            )
            .limit(1)
        )
        result = await self._session.execute(statement)
        return result.first() is not None

    async def bulk_update_sort_order(self, updates: list[tuple[uuid.UUID, int]]) -> None:
        """Bulk-update sort_order for multiple values in a single statement."""
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
