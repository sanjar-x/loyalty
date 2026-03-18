"""
AttributeGroup repository -- Data Mapper implementation.

Translates between :class:`~src.modules.catalog.domain.entities.AttributeGroup`
(domain) and the ``attribute_groups`` ORM table.  Provides code-based lookups
and attribute membership checks for the delete guard.
"""

import uuid

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.domain.entities import AttributeGroup as DomainAttributeGroup
from src.modules.catalog.domain.interfaces import IAttributeGroupRepository
from src.modules.catalog.infrastructure.models import Attribute as OrmAttribute
from src.modules.catalog.infrastructure.models import (
    AttributeGroup as OrmAttributeGroup,
)


class AttributeGroupRepository(IAttributeGroupRepository):
    """Data Mapper repository for the AttributeGroup aggregate.

    Converts between the database layer (``OrmAttributeGroup``) and the domain
    layer (``DomainAttributeGroup``), keeping ORM concerns out of business logic.

    Args:
        session: SQLAlchemy async session scoped to the current request.
    """

    def __init__(self, session: AsyncSession):
        self._session = session

    def _to_domain(self, orm: OrmAttributeGroup) -> DomainAttributeGroup:
        """Map an ORM AttributeGroup row to a domain AttributeGroup entity."""
        return DomainAttributeGroup(
            id=orm.id,
            code=orm.code,
            name_i18n=dict(orm.name_i18n) if orm.name_i18n else {},
            sort_order=orm.sort_order,
        )

    def _to_orm(
        self, domain: DomainAttributeGroup, orm: OrmAttributeGroup | None = None
    ) -> OrmAttributeGroup:
        """Map a domain AttributeGroup entity to an ORM row (create or update)."""
        if orm is None:
            orm = OrmAttributeGroup()
        orm.id = domain.id
        orm.code = domain.code
        orm.name_i18n = domain.name_i18n  # type: ignore[assignment]
        orm.sort_order = domain.sort_order
        return orm

    async def add(self, entity: DomainAttributeGroup) -> DomainAttributeGroup:
        """Persist a new attribute group and return the refreshed domain entity."""
        orm = self._to_orm(entity)
        self._session.add(orm)
        await self._session.flush()
        return self._to_domain(orm)

    async def get(self, entity_id: uuid.UUID) -> DomainAttributeGroup | None:
        """Retrieve an attribute group by primary key, or ``None`` if not found."""
        orm = await self._session.get(OrmAttributeGroup, entity_id)
        if orm:
            return self._to_domain(orm)
        return None

    async def update(self, entity: DomainAttributeGroup) -> DomainAttributeGroup:
        """Merge updated domain state into the existing ORM row.

        Raises:
            ValueError: If the group row does not exist.
        """
        orm = await self._session.get(OrmAttributeGroup, entity.id)
        if not orm:
            raise ValueError(f"AttributeGroup with id {entity.id} not found in DB")
        orm = self._to_orm(entity, orm)
        await self._session.flush()
        return self._to_domain(orm)

    async def delete(self, entity_id: uuid.UUID) -> None:
        """Delete an attribute group row by primary key."""
        statement = delete(OrmAttributeGroup).where(OrmAttributeGroup.id == entity_id)
        await self._session.execute(statement)

    async def check_code_exists(self, code: str) -> bool:
        """Return ``True`` if any attribute group already uses this code."""
        statement = select(OrmAttributeGroup.id).where(OrmAttributeGroup.code == code).limit(1)
        result = await self._session.execute(statement)
        return result.first() is not None

    async def get_by_code(self, code: str) -> DomainAttributeGroup | None:
        """Retrieve an attribute group by its unique code, or ``None``."""
        statement = select(OrmAttributeGroup).where(OrmAttributeGroup.code == code).limit(1)
        result = await self._session.execute(statement)
        orm = result.scalar_one_or_none()
        if orm:
            return self._to_domain(orm)
        return None

    async def has_attributes(self, group_id: uuid.UUID) -> bool:
        """Return ``True`` if at least one attribute belongs to this group."""
        statement = select(
            select(OrmAttribute.id).where(OrmAttribute.group_id == group_id).limit(1).exists()
        )
        result = await self._session.execute(statement)
        return bool(result.scalar())

    async def move_attributes_to_group(
        self, source_group_id: uuid.UUID, target_group_id: uuid.UUID
    ) -> None:
        """Bulk-move all attributes from one group to another."""
        statement = (
            update(OrmAttribute)
            .where(OrmAttribute.group_id == source_group_id)
            .values(group_id=target_group_id)
        )
        await self._session.execute(statement)
