"""
MediaAsset repository -- Data Mapper implementation.

Translates between :class:`~src.modules.catalog.domain.entities.MediaAsset`
(domain) and the ``media_assets`` ORM table.  Provides per-product listing,
pessimistic locking, and a MAIN-role existence check used by upload validation.
"""

import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.domain.entities import MediaAsset as DomainMediaAsset
from src.modules.catalog.domain.interfaces import IMediaAssetRepository
from src.modules.catalog.domain.value_objects import (
    MediaRole,
    MediaType,
)
from src.modules.catalog.infrastructure.models import MediaAsset as OrmMediaAsset


class MediaAssetRepository(IMediaAssetRepository):
    """Data Mapper repository for the MediaAsset child entity.

    Converts between the database layer (``OrmMediaAsset``) and the domain
    layer (``DomainMediaAsset``), keeping ORM concerns out of business logic.

    Note: This class does NOT inherit from ``BaseRepository`` because
    ``IMediaAssetRepository`` extends ``ABC`` directly (not
    ``ICatalogRepository``), and its method signatures use different
    parameter names (``media`` / ``media_id`` vs ``entity`` /
    ``entity_id``).  Aligning the interface hierarchy would be a
    larger refactor, so CRUD methods are kept inline here.

    Args:
        session: SQLAlchemy async session scoped to the current request.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # Mapping helpers
    # ------------------------------------------------------------------

    def _to_domain(self, orm: OrmMediaAsset) -> DomainMediaAsset:
        """Map an ORM MediaAsset row to a domain MediaAsset entity."""
        return DomainMediaAsset(
            id=orm.id,
            product_id=orm.product_id,
            variant_id=orm.variant_id,
            media_type=orm.media_type,
            role=orm.role,
            sort_order=orm.sort_order,
            is_external=orm.is_external,
            storage_object_id=orm.storage_object_id,
            url=orm.url,
            image_variants=orm.image_variants,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
        )

    def _to_orm(
        self, entity: DomainMediaAsset, orm: OrmMediaAsset | None = None
    ) -> OrmMediaAsset:
        """Map a domain MediaAsset entity to an ORM row (create or update)."""
        if orm is None:
            orm = OrmMediaAsset()
        orm.id = entity.id
        orm.product_id = entity.product_id
        orm.variant_id = entity.variant_id
        orm.media_type = MediaType(entity.media_type)
        orm.role = MediaRole(entity.role)
        orm.sort_order = entity.sort_order
        orm.is_external = entity.is_external
        orm.storage_object_id = entity.storage_object_id
        orm.url = entity.url
        orm.image_variants = entity.image_variants
        return orm

    # ------------------------------------------------------------------
    # IMediaAssetRepository methods
    # ------------------------------------------------------------------

    async def add(self, media: DomainMediaAsset) -> DomainMediaAsset:
        """Persist a new media asset."""
        orm = self._to_orm(media)
        self._session.add(orm)
        await self._session.flush()
        return self._to_domain(orm)

    async def get(self, media_id: uuid.UUID) -> DomainMediaAsset | None:
        """Retrieve a media asset by primary key, or ``None`` if not found."""
        orm = await self._session.get(OrmMediaAsset, media_id)
        if orm:
            return self._to_domain(orm)
        return None

    async def get_for_update(self, media_id: uuid.UUID) -> DomainMediaAsset | None:
        """Retrieve a media asset with a ``SELECT ... FOR UPDATE`` row lock."""
        stmt = (
            select(OrmMediaAsset).where(OrmMediaAsset.id == media_id).with_for_update()
        )
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    async def update(self, media: DomainMediaAsset) -> DomainMediaAsset:
        """Merge updated domain state into the existing ORM row.

        Raises:
            ValueError: If the media asset row does not exist.
        """
        orm = await self._session.get(OrmMediaAsset, media.id)
        if not orm:
            raise ValueError(f"MediaAsset with id {media.id} not found in DB")
        self._to_orm(media, orm)
        await self._session.flush()
        return self._to_domain(orm)

    async def delete(self, media_id: uuid.UUID) -> None:
        """Delete a media asset row by primary key."""
        stmt = delete(OrmMediaAsset).where(OrmMediaAsset.id == media_id)
        await self._session.execute(stmt)

    async def list_by_product(self, product_id: uuid.UUID) -> list[DomainMediaAsset]:
        """List all media assets for a product, ordered by (variant_id, sort_order)."""
        stmt = (
            select(OrmMediaAsset)
            .where(OrmMediaAsset.product_id == product_id)
            .order_by(OrmMediaAsset.variant_id, OrmMediaAsset.sort_order)
        )
        result = await self._session.execute(stmt)
        rows = result.scalars().all()
        return [self._to_domain(orm) for orm in rows]

    async def list_by_storage_ids(
        self,
        storage_object_ids: list[uuid.UUID],
    ) -> list[DomainMediaAsset]:
        """Get media assets by their storage_object_ids."""
        stmt = select(OrmMediaAsset).where(
            OrmMediaAsset.storage_object_id.in_(storage_object_ids)
        )
        result = await self._session.execute(stmt)
        return [self._to_domain(row) for row in result.scalars().all()]

    async def delete_by_product(self, product_id: uuid.UUID) -> list[uuid.UUID]:
        """Delete all media for a product. Returns storage_object_ids for cleanup."""
        # First collect storage_object_ids
        stmt = select(OrmMediaAsset.storage_object_id).where(
            OrmMediaAsset.product_id == product_id,
            OrmMediaAsset.storage_object_id.isnot(None),
        )
        result = await self._session.execute(stmt)
        sids = list(result.scalars().all())

        # Bulk delete
        del_stmt = delete(OrmMediaAsset).where(OrmMediaAsset.product_id == product_id)
        await self._session.execute(del_stmt)
        return sids
