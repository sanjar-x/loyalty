"""
MediaAsset repository — Data Mapper implementation.

Translates between :class:`~src.modules.catalog.domain.entities.MediaAsset`
(domain) and the ``media_assets`` ORM table.  Provides per-product listing,
pessimistic locking, and a MAIN-role existence check used by upload validation.
"""

import uuid

from sqlalchemy import delete, exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.domain.entities import MediaAsset as DomainMediaAsset
from src.modules.catalog.domain.interfaces import IMediaAssetRepository
from src.modules.catalog.domain.value_objects import MediaProcessingStatus
from src.modules.catalog.infrastructure.models import MediaAsset as OrmMediaAsset
from src.modules.catalog.infrastructure.models import MediaRole, MediaType


class MediaAssetRepository(IMediaAssetRepository):
    """Data Mapper repository for the MediaAsset child entity.

    Converts between the database layer (``OrmMediaAsset``) and the domain
    layer (``DomainMediaAsset``), keeping ORM concerns out of business logic.

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
        processing_status: MediaProcessingStatus | None = None
        if orm.processing_status is not None:
            processing_status = MediaProcessingStatus(orm.processing_status)

        return DomainMediaAsset(
            id=orm.id,
            product_id=orm.product_id,
            attribute_value_id=orm.attribute_value_id,
            media_type=orm.media_type.value,
            role=orm.role.value,
            sort_order=orm.sort_order,
            processing_status=processing_status,
            storage_object_id=orm.storage_object_id,
            is_external=orm.is_external,
            external_url=orm.external_url,
            raw_object_key=orm.raw_object_key,
            public_url=orm.public_url,
        )

    def _to_orm(self, entity: DomainMediaAsset, orm: OrmMediaAsset | None = None) -> OrmMediaAsset:
        """Map a domain MediaAsset entity to an ORM row (create or update)."""
        if orm is None:
            orm = OrmMediaAsset()
        orm.id = entity.id
        orm.product_id = entity.product_id
        orm.attribute_value_id = entity.attribute_value_id
        orm.media_type = MediaType(entity.media_type)
        orm.role = MediaRole(entity.role)
        orm.sort_order = entity.sort_order
        orm.processing_status = (
            entity.processing_status.value if entity.processing_status is not None else None
        )
        orm.storage_object_id = entity.storage_object_id
        orm.is_external = entity.is_external
        orm.external_url = entity.external_url
        orm.raw_object_key = entity.raw_object_key
        orm.public_url = entity.public_url
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
        """Retrieve a media asset with a ``SELECT … FOR UPDATE`` row lock."""
        stmt = select(OrmMediaAsset).where(OrmMediaAsset.id == media_id).with_for_update()
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
        """List all media assets for a product, ordered by (attribute_value_id, sort_order)."""
        stmt = (
            select(OrmMediaAsset)
            .where(OrmMediaAsset.product_id == product_id)
            .order_by(OrmMediaAsset.attribute_value_id, OrmMediaAsset.sort_order)
        )
        result = await self._session.execute(stmt)
        rows = result.scalars().all()
        return [self._to_domain(orm) for orm in rows]

    async def has_main_for_variant(
        self,
        product_id: uuid.UUID,
        attribute_value_id: uuid.UUID | None,
    ) -> bool:
        """Check if a MAIN media asset already exists for this product/variant combo."""
        if attribute_value_id is None:
            condition = (
                (OrmMediaAsset.product_id == product_id)
                & (OrmMediaAsset.attribute_value_id.is_(None))
                & (OrmMediaAsset.role == MediaRole.MAIN)
                & (OrmMediaAsset.processing_status != MediaProcessingStatus.FAILED.value)
            )
        else:
            condition = (
                (OrmMediaAsset.product_id == product_id)
                & (OrmMediaAsset.attribute_value_id == attribute_value_id)
                & (OrmMediaAsset.role == MediaRole.MAIN)
                & (OrmMediaAsset.processing_status != MediaProcessingStatus.FAILED.value)
            )
        stmt = select(exists().where(condition))
        result = await self._session.execute(stmt)
        return bool(result.scalar())
