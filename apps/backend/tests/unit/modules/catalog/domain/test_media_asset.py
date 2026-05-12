"""Unit tests for the MediaAsset record entity.

MediaAsset uses @define (not @dataclass), is NOT an AggregateRoot,
has NO update() method, and emits NO domain events.
Only tests the create() factory and its validation paths.
"""

import uuid

import pytest

from src.modules.catalog.domain.entities import MediaAsset
from src.modules.catalog.domain.value_objects import MediaRole, MediaType
from tests.factories.media_asset_builder import MediaAssetBuilder

# ---------------------------------------------------------------------------
# TestMediaAssetCreate
# ---------------------------------------------------------------------------


class TestMediaAssetCreate:
    """MediaAsset.create() factory -- happy paths and validation."""

    def test_create_valid(self):
        asset = MediaAssetBuilder().build()
        assert isinstance(asset.id, uuid.UUID)
        assert asset.media_type == MediaType.IMAGE
        assert asset.role == MediaRole.GALLERY

    def test_create_with_string_media_type(self):
        asset = MediaAsset.create(
            product_id=uuid.uuid4(),
            media_type="image",
            role=MediaRole.GALLERY,
        )
        assert asset.media_type == MediaType.IMAGE

    def test_create_with_string_role(self):
        asset = MediaAsset.create(
            product_id=uuid.uuid4(),
            media_type=MediaType.IMAGE,
            role="gallery",
        )
        assert asset.role == MediaRole.GALLERY

    def test_create_rejects_invalid_media_type_string(self):
        with pytest.raises(ValueError, match="Invalid media_type"):
            MediaAsset.create(
                product_id=uuid.uuid4(),
                media_type="INVALID",
                role=MediaRole.GALLERY,
            )

    def test_create_rejects_invalid_role_string(self):
        with pytest.raises(ValueError, match="Invalid role"):
            MediaAsset.create(
                product_id=uuid.uuid4(),
                media_type=MediaType.IMAGE,
                role="INVALID",
            )

    def test_create_rejects_negative_sort_order(self):
        with pytest.raises(ValueError, match="sort_order must be non-negative"):
            MediaAsset.create(
                product_id=uuid.uuid4(),
                media_type=MediaType.IMAGE,
                role=MediaRole.GALLERY,
                sort_order=-1,
            )

    def test_create_external_requires_url(self):
        with pytest.raises(ValueError, match="External media assets must have a URL"):
            MediaAsset.create(
                product_id=uuid.uuid4(),
                media_type=MediaType.IMAGE,
                role=MediaRole.GALLERY,
                is_external=True,
                url=None,
            )

    def test_create_external_with_url(self):
        asset = MediaAsset.create(
            product_id=uuid.uuid4(),
            media_type=MediaType.IMAGE,
            role=MediaRole.GALLERY,
            is_external=True,
            url="https://cdn.example.com/img.jpg",
        )
        assert asset.is_external is True
        assert asset.url == "https://cdn.example.com/img.jpg"

    def test_create_with_variant_id(self):
        variant_id = uuid.uuid4()
        asset = MediaAsset.create(
            product_id=uuid.uuid4(),
            variant_id=variant_id,
            media_type=MediaType.IMAGE,
            role=MediaRole.GALLERY,
        )
        assert asset.variant_id == variant_id

    def test_create_with_storage_object_id(self):
        storage_id = uuid.uuid4()
        asset = MediaAsset.create(
            product_id=uuid.uuid4(),
            media_type=MediaType.IMAGE,
            role=MediaRole.GALLERY,
            storage_object_id=storage_id,
        )
        assert asset.storage_object_id == storage_id

    def test_create_with_image_variants(self):
        img_variants = [
            {"size": "thumbnail", "url": "https://cdn.example.com/thumb.jpg"}
        ]
        asset = MediaAsset.create(
            product_id=uuid.uuid4(),
            media_type=MediaType.IMAGE,
            role=MediaRole.GALLERY,
            image_variants=img_variants,
        )
        assert asset.image_variants == img_variants
