"""Query handler for listing product media assets."""

import uuid
from dataclasses import dataclass

from src.modules.catalog.domain.entities import MediaAsset
from src.modules.catalog.domain.interfaces import IMediaAssetRepository


@dataclass(frozen=True)
class MediaAssetReadModel:
    """Read-only DTO for a media asset."""

    id: uuid.UUID
    product_id: uuid.UUID
    attribute_value_id: uuid.UUID | None
    media_type: str
    role: str
    sort_order: int
    processing_status: str | None
    public_url: str | None
    is_external: bool
    external_url: str | None


def _to_read_model(media: MediaAsset) -> MediaAssetReadModel:
    return MediaAssetReadModel(
        id=media.id,
        product_id=media.product_id,
        attribute_value_id=media.attribute_value_id,
        media_type=media.media_type,
        role=media.role,
        sort_order=media.sort_order,
        processing_status=media.processing_status.value if media.processing_status else None,
        public_url=media.public_url,
        is_external=media.is_external,
        external_url=media.external_url,
    )


class ListProductMediaHandler:
    def __init__(self, media_repo: IMediaAssetRepository) -> None:
        self._media_repo = media_repo

    async def handle(self, product_id: uuid.UUID) -> list[MediaAssetReadModel]:
        media_list = await self._media_repo.list_by_product(product_id)
        return [_to_read_model(m) for m in media_list]
