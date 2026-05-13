"""
AttributeGroup repository -- Data Mapper implementation.

Translates between :class:`~src.modules.catalog.domain.entities.AttributeGroup`
(domain) and the ``attribute_groups`` ORM table.  Provides code-based lookups
and attribute membership checks for the delete guard.
"""

import uuid

from sqlalchemy import select, update

from src.modules.catalog.domain.entities import AttributeGroup as DomainAttributeGroup
from src.modules.catalog.domain.interfaces import IAttributeGroupRepository
from src.modules.catalog.infrastructure.models import Attribute as OrmAttribute
from src.modules.catalog.infrastructure.models import (
    AttributeGroup as OrmAttributeGroup,
)
from src.modules.catalog.infrastructure.repositories.base import BaseRepository


class AttributeGroupRepository(
    BaseRepository[DomainAttributeGroup, OrmAttributeGroup],
    IAttributeGroupRepository,
    model_class=OrmAttributeGroup,
):
    """Data Mapper repository for the AttributeGroup aggregate.

    Inherits generic CRUD from :class:`BaseRepository` and adds
    code-based lookups and attribute membership operations.
    """

    def _to_domain(self, orm: OrmAttributeGroup) -> DomainAttributeGroup:
        """Map an ORM AttributeGroup row to a domain AttributeGroup entity."""
        return DomainAttributeGroup(
            id=orm.id,
            code=orm.code,
            name_i18n=dict(orm.name_i18n) if orm.name_i18n else {},
            sort_order=orm.sort_order,
        )

    def _to_orm(
        self, entity: DomainAttributeGroup, orm: OrmAttributeGroup | None = None
    ) -> OrmAttributeGroup:
        """Map a domain AttributeGroup entity to an ORM row (create or update)."""
        if orm is None:
            orm = OrmAttributeGroup()
        orm.id = entity.id
        orm.code = entity.code
        orm.name_i18n = entity.name_i18n
        orm.sort_order = entity.sort_order
        return orm

    async def check_code_exists(self, code: str) -> bool:
        """Return ``True`` if any attribute group already uses this code."""
        stmt = (
            select(OrmAttributeGroup.id).where(OrmAttributeGroup.code == code).limit(1)
        )
        result = await self._session.execute(stmt)
        return result.first() is not None

    async def get_by_code(self, code: str) -> DomainAttributeGroup | None:
        """Retrieve an attribute group by its unique code, or ``None``."""
        stmt = select(OrmAttributeGroup).where(OrmAttributeGroup.code == code).limit(1)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        if orm:
            return self._to_domain(orm)
        return None

    async def has_attributes(self, group_id: uuid.UUID) -> bool:
        """Return ``True`` if at least one attribute belongs to this group."""
        stmt = select(
            select(OrmAttribute.id)
            .where(OrmAttribute.group_id == group_id)
            .limit(1)
            .exists()
        )
        result = await self._session.execute(stmt)
        return bool(result.scalar())

    async def move_attributes_to_group(
        self, source_group_id: uuid.UUID, target_group_id: uuid.UUID
    ) -> None:
        """Bulk-move all attributes from one group to another."""
        stmt = (
            update(OrmAttribute)
            .where(OrmAttribute.group_id == source_group_id)
            .values(group_id=target_group_id)
        )
        await self._session.execute(stmt)
