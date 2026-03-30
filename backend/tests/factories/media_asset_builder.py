# tests/factories/media_asset_builder.py
"""Fluent Builder for the MediaAsset domain entity.

CRITICAL: When as_external(url) is used, is_external is set to True AND
url is set. Otherwise MediaAsset.create() raises ValueError.
"""

from __future__ import annotations

import uuid

from src.modules.catalog.domain.entities import MediaAsset
from src.modules.catalog.domain.value_objects import MediaRole, MediaType


class MediaAssetBuilder:
    """Fluent builder for MediaAsset entities with sensible defaults.

    Usage:
        asset = MediaAssetBuilder().build()
        asset = (
            MediaAssetBuilder()
            .with_product_id(product.id)
            .as_external("https://example.com/img.jpg")
            .build()
        )
    """

    def __init__(self) -> None:
        self._product_id: uuid.UUID | None = None
        self._variant_id: uuid.UUID | None = None
        self._media_type: MediaType = MediaType.IMAGE
        self._role: MediaRole = MediaRole.GALLERY
        self._sort_order: int = 0
        self._is_external: bool = False
        self._storage_object_id: uuid.UUID | None = None
        self._url: str | None = None
        self._image_variants: list[dict] | None = None

    def with_product_id(self, product_id: uuid.UUID) -> MediaAssetBuilder:
        self._product_id = product_id
        return self

    def with_variant_id(self, variant_id: uuid.UUID) -> MediaAssetBuilder:
        self._variant_id = variant_id
        return self

    def with_media_type(self, media_type: MediaType) -> MediaAssetBuilder:
        self._media_type = media_type
        return self

    def with_role(self, role: MediaRole) -> MediaAssetBuilder:
        self._role = role
        return self

    def with_sort_order(self, sort_order: int) -> MediaAssetBuilder:
        self._sort_order = sort_order
        return self

    def as_external(self, url: str) -> MediaAssetBuilder:
        """Mark this asset as externally hosted with the given URL."""
        self._is_external = True
        self._url = url
        return self

    def with_storage_object_id(self, storage_object_id: uuid.UUID) -> MediaAssetBuilder:
        self._storage_object_id = storage_object_id
        return self

    def with_image_variants(self, image_variants: list[dict]) -> MediaAssetBuilder:
        self._image_variants = image_variants
        return self

    def build(self) -> MediaAsset:
        """Build a MediaAsset via MediaAsset.create() factory method."""
        product_id = self._product_id or uuid.uuid4()
        return MediaAsset.create(
            product_id=product_id,
            variant_id=self._variant_id,
            media_type=self._media_type,
            role=self._role,
            sort_order=self._sort_order,
            is_external=self._is_external,
            storage_object_id=self._storage_object_id,
            url=self._url,
            image_variants=self._image_variants,
        )
