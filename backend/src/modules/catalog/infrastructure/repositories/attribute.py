"""
Attribute repository -- Data Mapper implementation.

Translates between :class:`~src.modules.catalog.domain.entities.Attribute`
(domain) and the ``attributes`` ORM table. Provides code/slug-based lookups
and category binding checks for delete guards.
"""

import uuid

from sqlalchemy import select

from src.modules.catalog.domain.entities import Attribute as DomainAttribute
from src.modules.catalog.domain.interfaces import IAttributeRepository
from src.modules.catalog.domain.value_objects import BehaviorFlags
from src.modules.catalog.infrastructure.models import Attribute as OrmAttribute
from src.modules.catalog.infrastructure.models import (
    ProductAttributeValue as OrmProductAttributeValue,
)
from src.modules.catalog.infrastructure.repositories.base import BaseRepository


class AttributeRepository(
    BaseRepository[DomainAttribute, OrmAttribute],
    IAttributeRepository,
    model_class=OrmAttribute,
):
    """Data Mapper repository for the Attribute aggregate.

    Inherits generic CRUD from :class:`BaseRepository` and adds
    code/slug-based lookups and category binding checks.
    """

    def _to_domain(self, orm: OrmAttribute) -> DomainAttribute:
        """Map an ORM Attribute row to a domain Attribute entity."""
        return DomainAttribute(
            id=orm.id,
            code=orm.code,
            slug=orm.slug,
            name_i18n=dict(orm.name_i18n) if orm.name_i18n else {},
            description_i18n=dict(orm.description_i18n) if orm.description_i18n else {},
            data_type=orm.data_type,
            ui_type=orm.ui_type,
            is_dictionary=orm.is_dictionary,
            group_id=orm.group_id,
            level=orm.level,
            behavior=BehaviorFlags(
                is_filterable=bool(orm.is_filterable),
                is_searchable=bool(orm.is_searchable),
                search_weight=orm.search_weight,
                is_comparable=bool(orm.is_comparable),
                is_visible_on_card=bool(orm.is_visible_on_card),
            ),
            validation_rules=dict(orm.validation_rules)
            if orm.validation_rules
            else None,
        )

    def _to_orm(
        self, entity: DomainAttribute, orm: OrmAttribute | None = None
    ) -> OrmAttribute:
        """Map a domain Attribute entity to an ORM row (create or update)."""
        if orm is None:
            orm = OrmAttribute()
        orm.id = entity.id
        orm.code = entity.code
        orm.slug = entity.slug
        orm.name_i18n = entity.name_i18n
        orm.description_i18n = entity.description_i18n
        orm.data_type = entity.data_type
        orm.ui_type = entity.ui_type
        orm.is_dictionary = entity.is_dictionary
        orm.group_id = entity.group_id
        orm.level = entity.level
        orm.is_filterable = entity.is_filterable
        orm.is_searchable = entity.is_searchable
        orm.search_weight = entity.search_weight
        orm.is_comparable = entity.is_comparable
        orm.is_visible_on_card = entity.is_visible_on_card
        orm.validation_rules = entity.validation_rules
        return orm

    async def get_many(self, ids: list[uuid.UUID]) -> dict[uuid.UUID, DomainAttribute]:
        """Batch-load multiple attributes by their UUIDs."""
        if not ids:
            return {}
        stmt = select(OrmAttribute).where(OrmAttribute.id.in_(ids))
        result = await self._session.execute(stmt)
        return {orm.id: self._to_domain(orm) for orm in result.scalars().all()}

    async def check_code_exists(self, code: str) -> bool:
        """Return ``True`` if any attribute already uses this code."""
        return await self._field_exists("code", code)

    async def check_slug_exists(self, slug: str) -> bool:
        """Return ``True`` if any attribute already uses this slug."""
        return await self._field_exists("slug", slug)

    async def has_product_attribute_values(self, attribute_id: uuid.UUID) -> bool:
        """Return ``True`` if any products reference this attribute."""
        stmt = select(
            select(OrmProductAttributeValue.id)
            .where(OrmProductAttributeValue.attribute_id == attribute_id)
            .limit(1)
            .exists()
        )
        result = await self._session.execute(stmt)
        return bool(result.scalar())
