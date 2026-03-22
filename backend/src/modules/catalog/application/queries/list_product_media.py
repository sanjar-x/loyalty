"""Query handler for listing product media assets."""

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.infrastructure.models import MediaAsset as OrmMediaAsset


@dataclass(frozen=True)
class MediaAssetReadModel:
    """Read-only DTO for a media asset."""

    id: uuid.UUID
    product_id: uuid.UUID
    variant_id: uuid.UUID | None
    media_type: str
    role: str
    sort_order: int
    processing_status: str | None
    public_url: str | None
    is_external: bool
    external_url: str | None


class ListProductMediaHandler:
    """List all media assets for a product (CQRS read side)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def handle(self, product_id: uuid.UUID) -> list[MediaAssetReadModel]:
        stmt = (
            select(OrmMediaAsset)
            .where(OrmMediaAsset.product_id == product_id)
            .order_by(OrmMediaAsset.variant_id, OrmMediaAsset.sort_order)
        )
        result = await self._session.execute(stmt)
        rows = result.scalars().all()
        return [self._to_read_model(orm) for orm in rows]

    @staticmethod
    def _to_read_model(orm: OrmMediaAsset) -> MediaAssetReadModel:
        return MediaAssetReadModel(
            id=orm.id,
            product_id=orm.product_id,
            variant_id=orm.variant_id,
            media_type=orm.media_type.value if orm.media_type else "",
            role=orm.role.value if orm.role else "",
            sort_order=orm.sort_order,
            processing_status=orm.processing_status,
            public_url=orm.public_url,
            is_external=orm.is_external,
            external_url=orm.external_url,
        )
