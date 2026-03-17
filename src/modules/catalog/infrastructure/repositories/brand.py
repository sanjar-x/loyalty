"""
Brand repository — Data Mapper implementation.

Translates between :class:`~src.modules.catalog.domain.entities.Brand`
(domain) and the ``brands`` ORM table.  Provides slug-based lookups and
a ``FOR UPDATE`` lock method used by the logo processing pipeline.
"""

import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.domain.entities import Brand as DomainBrand
from src.modules.catalog.domain.interfaces import IBrandRepository
from src.modules.catalog.infrastructure.models import Brand as OrmBrand


class BrandRepository(IBrandRepository):
    """Data Mapper repository for the Brand aggregate.

    Converts between the database layer (``OrmBrand``) and the domain
    layer (``DomainBrand``), keeping ORM concerns out of business logic.

    Args:
        session: SQLAlchemy async session scoped to the current request.
    """

    def __init__(self, session: AsyncSession):
        self._session = session

    def _to_domain(self, orm: OrmBrand) -> DomainBrand:
        """Map an ORM Brand row to a domain Brand entity."""
        return DomainBrand(
            id=orm.id,
            name=orm.name,
            slug=orm.slug,
            logo_status=orm.logo_status,
            logo_file_id=orm.logo_file_id,
            logo_url=orm.logo_url,
        )

    def _to_orm(self, domain: DomainBrand, orm: OrmBrand | None = None) -> OrmBrand:
        """Map a domain Brand entity to an ORM row (create or update)."""
        if orm is None:
            orm = OrmBrand()
        orm.id = domain.id
        orm.name = domain.name
        orm.slug = domain.slug
        orm.logo_status = domain.logo_status
        orm.logo_file_id = domain.logo_file_id
        orm.logo_url = domain.logo_url
        return orm

    async def add(self, entity: DomainBrand) -> DomainBrand:
        """Persist a new brand and return the refreshed domain entity."""
        orm = self._to_orm(entity)
        self._session.add(orm)
        await self._session.flush()
        return self._to_domain(orm)

    async def get(self, entity_id: uuid.UUID) -> DomainBrand | None:
        """Retrieve a brand by primary key, or ``None`` if not found."""
        orm = await self._session.get(OrmBrand, entity_id)
        if orm:
            return self._to_domain(orm)
        return None

    async def update(self, entity: DomainBrand) -> DomainBrand:
        """Merge updated domain state into the existing ORM row.

        Raises:
            ValueError: If the brand row does not exist.
        """
        orm = await self._session.get(OrmBrand, entity.id)
        if not orm:
            raise ValueError(f"Brand with id {entity.id} not found in DB")
        orm = self._to_orm(entity, orm)
        await self._session.flush()
        return self._to_domain(orm)

    async def delete(self, entity_id: uuid.UUID) -> None:
        """Delete a brand row by primary key."""
        statement = delete(OrmBrand).where(OrmBrand.id == entity_id)
        await self._session.execute(statement)

    async def get_by_slug(self, slug: str) -> DomainBrand | None:
        """Look up a brand by its URL slug, or ``None`` if not found."""
        statement = select(OrmBrand).where(OrmBrand.slug == slug).limit(1)
        result = await self._session.execute(statement)
        orm = result.scalar_one_or_none()
        if orm:
            return self._to_domain(orm)
        return None

    async def check_slug_exists(self, slug: str) -> bool:
        """Return ``True`` if any brand already uses this slug."""
        statement = select(OrmBrand.id).where(OrmBrand.slug == slug).limit(1)
        result = await self._session.execute(statement)
        return result.first() is not None

    async def check_slug_exists_excluding(self, slug: str, exclude_id: uuid.UUID) -> bool:
        """Return ``True`` if the slug is taken by a brand other than *exclude_id*."""
        statement = (
            select(OrmBrand.id).where(OrmBrand.slug == slug, OrmBrand.id != exclude_id).limit(1)
        )
        result = await self._session.execute(statement)
        return result.first() is not None

    async def get_for_update(self, brand_id: uuid.UUID) -> DomainBrand | None:
        """Retrieve a brand with a ``SELECT … FOR UPDATE`` row lock.

        Used by the logo processing pipeline to prevent concurrent
        state transitions on the same brand.
        """
        statement = select(OrmBrand).where(OrmBrand.id == brand_id).with_for_update()
        result = await self._session.execute(statement)
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None
