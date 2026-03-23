"""
Brand repository — Data Mapper implementation.

Translates between :class:`~src.modules.catalog.domain.entities.Brand`
(domain) and the ``brands`` ORM table.  Provides slug-based lookups and
a ``FOR UPDATE`` lock method used by the logo processing pipeline.
"""

import uuid

from sqlalchemy import select

from src.modules.catalog.domain.entities import Brand as DomainBrand
from src.modules.catalog.domain.interfaces import IBrandRepository
from src.modules.catalog.infrastructure.models import Brand as OrmBrand
from src.modules.catalog.infrastructure.repositories.base import BaseRepository


class BrandRepository(
    BaseRepository[DomainBrand, OrmBrand],
    IBrandRepository,
    model_class=OrmBrand,
):
    """Data Mapper repository for the Brand aggregate.

    Inherits generic CRUD from :class:`BaseRepository` and adds
    slug-based lookups and pessimistic locking.
    """

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

    def _to_orm(self, entity: DomainBrand, orm: OrmBrand | None = None) -> OrmBrand:
        """Map a domain Brand entity to an ORM row (create or update)."""
        if orm is None:
            orm = OrmBrand()
        orm.id = entity.id
        orm.name = entity.name
        orm.slug = entity.slug
        orm.logo_status = entity.logo_status
        orm.logo_file_id = entity.logo_file_id
        orm.logo_url = entity.logo_url
        return orm

    async def get_by_slug(self, slug: str) -> DomainBrand | None:
        """Look up a brand by its URL slug, or ``None`` if not found."""
        stmt = select(OrmBrand).where(OrmBrand.slug == slug).limit(1)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        if orm:
            return self._to_domain(orm)
        return None

    async def check_slug_exists(self, slug: str) -> bool:
        """Return ``True`` if any brand already uses this slug."""
        stmt = select(OrmBrand.id).where(OrmBrand.slug == slug).limit(1)
        result = await self._session.execute(stmt)
        return result.first() is not None

    async def check_slug_exists_excluding(self, slug: str, exclude_id: uuid.UUID) -> bool:
        """Return ``True`` if the slug is taken by a brand other than *exclude_id*."""
        stmt = select(OrmBrand.id).where(OrmBrand.slug == slug, OrmBrand.id != exclude_id).limit(1)
        result = await self._session.execute(stmt)
        return result.first() is not None

    # get_for_update is inherited from BaseRepository
