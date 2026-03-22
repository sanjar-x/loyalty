"""
Attribute repository -- Data Mapper implementation.

Translates between :class:`~src.modules.catalog.domain.entities.Attribute`
(domain) and the ``attributes`` ORM table. Provides code/slug-based lookups
and category binding checks for delete guards.
"""

import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.domain.entities import Attribute as DomainAttribute
from src.modules.catalog.domain.interfaces import IAttributeRepository
from src.modules.catalog.infrastructure.models import Attribute as OrmAttribute
from src.modules.catalog.infrastructure.models import (
    CategoryAttributeBinding as OrmCategoryAttributeBinding,
)


class AttributeRepository(IAttributeRepository):
    """Data Mapper repository for the Attribute aggregate.

    Converts between the database layer (``OrmAttribute``) and the domain
    layer (``DomainAttribute``), keeping ORM concerns out of business logic.

    Args:
        session: SQLAlchemy async session scoped to the current request.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

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
            group_id=orm.group_id,  # type: ignore[arg-type]
            level=orm.level,
            is_filterable=orm.is_filterable,
            is_searchable=orm.is_searchable,
            search_weight=orm.search_weight,
            is_comparable=orm.is_comparable,
            is_visible_on_card=orm.is_visible_on_card,
            is_visible_in_catalog=orm.is_visible_in_catalog,
            validation_rules=dict(orm.validation_rules) if orm.validation_rules else None,
        )

    def _to_orm(self, entity: DomainAttribute, orm: OrmAttribute | None = None) -> OrmAttribute:
        """Map a domain Attribute entity to an ORM row (create or update)."""
        if orm is None:
            orm = OrmAttribute()
        orm.id = entity.id
        orm.code = entity.code
        orm.slug = entity.slug
        orm.name_i18n = entity.name_i18n  # type: ignore[assignment]
        orm.description_i18n = entity.description_i18n  # type: ignore[assignment]
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
        orm.is_visible_in_catalog = entity.is_visible_in_catalog
        orm.validation_rules = entity.validation_rules  # type: ignore[assignment]
        return orm

    async def add(self, entity: DomainAttribute) -> DomainAttribute:
        """Persist a new attribute and return the refreshed domain entity."""
        orm = self._to_orm(entity)
        self._session.add(orm)
        await self._session.flush()
        return self._to_domain(orm)

    async def get(self, entity_id: uuid.UUID) -> DomainAttribute | None:
        """Retrieve an attribute by primary key, or ``None`` if not found."""
        orm = await self._session.get(OrmAttribute, entity_id)
        if orm:
            return self._to_domain(orm)
        return None

    async def update(self, entity: DomainAttribute) -> DomainAttribute:
        """Merge updated domain state into the existing ORM row.

        Raises:
            ValueError: If the attribute row does not exist.
        """
        orm = await self._session.get(OrmAttribute, entity.id)
        if not orm:
            raise ValueError(f"Attribute with id {entity.id} not found in DB")
        orm = self._to_orm(entity, orm)
        await self._session.flush()
        return self._to_domain(orm)

    async def delete(self, entity_id: uuid.UUID) -> None:
        """Delete an attribute row by primary key."""
        stmt = delete(OrmAttribute).where(OrmAttribute.id == entity_id)
        await self._session.execute(stmt)

    async def check_code_exists(self, code: str) -> bool:
        """Return ``True`` if any attribute already uses this code."""
        stmt = select(OrmAttribute.id).where(OrmAttribute.code == code).limit(1)
        result = await self._session.execute(stmt)
        return result.first() is not None

    async def check_slug_exists(self, slug: str) -> bool:
        """Return ``True`` if any attribute already uses this slug."""
        stmt = select(OrmAttribute.id).where(OrmAttribute.slug == slug).limit(1)
        result = await self._session.execute(stmt)
        return result.first() is not None

    async def check_code_exists_excluding(self, code: str, exclude_id: uuid.UUID) -> bool:
        """Return ``True`` if the code is taken by another attribute."""
        stmt = (
            select(OrmAttribute.id)
            .where(OrmAttribute.code == code, OrmAttribute.id != exclude_id)
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.first() is not None

    async def check_slug_exists_excluding(self, slug: str, exclude_id: uuid.UUID) -> bool:
        """Return ``True`` if the slug is taken by another attribute."""
        stmt = (
            select(OrmAttribute.id)
            .where(OrmAttribute.slug == slug, OrmAttribute.id != exclude_id)
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.first() is not None

    async def get_by_slug(self, slug: str) -> DomainAttribute | None:
        """Retrieve an attribute by its URL slug, or ``None`` if not found."""
        stmt = select(OrmAttribute).where(OrmAttribute.slug == slug).limit(1)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        if orm:
            return self._to_domain(orm)
        return None

    async def has_category_bindings(self, attribute_id: uuid.UUID) -> bool:
        """Return ``True`` if the attribute is bound to at least one category."""
        stmt = select(
            select(OrmCategoryAttributeBinding.id)
            .where(OrmCategoryAttributeBinding.attribute_id == attribute_id)
            .limit(1)
            .exists()
        )
        result = await self._session.execute(stmt)
        return bool(result.scalar())
