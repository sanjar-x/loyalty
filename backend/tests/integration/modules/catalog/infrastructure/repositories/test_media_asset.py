"""
Integration tests for MediaAssetRepository Data Mapper roundtrips.

Proves that MediaAsset entities survive CRUD cycles with enum mapping
(MediaType, MediaRole), JSONB image_variants, nullable fields,
list_by_product ordering, and bulk_update_sort_order.

Part of Phase 07 -- Repository & Data Integrity (REPO-02, REPO-05).
"""

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.domain.entities import MediaAsset, Product
from src.modules.catalog.domain.value_objects import MediaRole, MediaType
from src.modules.catalog.infrastructure.repositories.media_asset import (
    MediaAssetRepository,
)
from src.modules.catalog.infrastructure.repositories.product import ProductRepository


@pytest.fixture()
async def _seed_product(
    db_session: AsyncSession,
    seed_product_deps: dict[str, uuid.UUID],
) -> Product:
    """Create a minimal Product for MediaAsset FK satisfaction."""
    repo = ProductRepository(session=db_session)
    product = Product.create(
        slug="media-test-product",
        title_i18n={"en": "Media Product", "ru": "Медиа продукт"},
        brand_id=seed_product_deps["brand_id"],
        primary_category_id=seed_product_deps["category_id"],
    )
    await repo.add(product)
    await db_session.flush()
    return product


class TestMediaAssetRoundtrip:
    """Verify MediaAsset entity survives full create-read roundtrip."""

    async def test_media_asset_basic_roundtrip(
        self,
        db_session: AsyncSession,
        _seed_product: Product,
    ) -> None:
        """All MediaAsset fields including enums and JSONB survive roundtrip."""
        repo = MediaAssetRepository(session=db_session)
        storage_id = uuid.uuid4()
        asset = MediaAsset.create(
            product_id=_seed_product.id,
            variant_id=None,
            media_type=MediaType.IMAGE,
            role=MediaRole.GALLERY,
            sort_order=0,
            is_external=False,
            storage_object_id=storage_id,
            url="https://cdn.example.com/img.jpg",
            image_variants=[
                {
                    "size": "thumb",
                    "width": 100,
                    "height": 100,
                    "url": "https://cdn.example.com/thumb.jpg",
                }
            ],
        )
        await repo.add(asset)
        await db_session.flush()

        fetched = await repo.get(asset.id)

        assert fetched is not None
        assert fetched.media_type == MediaType.IMAGE
        assert isinstance(fetched.media_type, MediaType)
        assert fetched.role == MediaRole.GALLERY
        assert isinstance(fetched.role, MediaRole)
        assert fetched.image_variants == [
            {
                "size": "thumb",
                "width": 100,
                "height": 100,
                "url": "https://cdn.example.com/thumb.jpg",
            }
        ]
        assert fetched.url == "https://cdn.example.com/img.jpg"
        assert fetched.is_external is False
        assert fetched.storage_object_id == storage_id

    async def test_media_asset_nullable_fields(
        self,
        db_session: AsyncSession,
        _seed_product: Product,
    ) -> None:
        """Nullable fields preserve None."""
        repo = MediaAssetRepository(session=db_session)
        asset = MediaAsset.create(
            product_id=_seed_product.id,
            variant_id=None,
            media_type=MediaType.IMAGE,
            role=MediaRole.GALLERY,
            sort_order=0,
            storage_object_id=None,
            url=None,
            image_variants=None,
        )
        await repo.add(asset)
        await db_session.flush()

        fetched = await repo.get(asset.id)

        assert fetched is not None
        assert fetched.variant_id is None
        assert fetched.storage_object_id is None
        assert fetched.url is None
        assert fetched.image_variants is None

    async def test_list_by_product(
        self,
        db_session: AsyncSession,
        _seed_product: Product,
    ) -> None:
        """list_by_product returns assets sorted by sort_order."""
        repo = MediaAssetRepository(session=db_session)
        for sort in [2, 0, 1]:
            asset = MediaAsset.create(
                product_id=_seed_product.id,
                media_type=MediaType.IMAGE,
                role=MediaRole.GALLERY,
                sort_order=sort,
            )
            await repo.add(asset)
        await db_session.flush()

        result = await repo.list_by_product(_seed_product.id)

        assert len(result) == 3
        assert [a.sort_order for a in result] == [0, 1, 2]

    async def test_check_main_exists(
        self,
        db_session: AsyncSession,
        _seed_product: Product,
    ) -> None:
        """check_main_exists detects MAIN media correctly."""
        repo = MediaAssetRepository(session=db_session)
        asset = MediaAsset.create(
            product_id=_seed_product.id,
            variant_id=None,
            media_type=MediaType.IMAGE,
            role=MediaRole.MAIN,
            sort_order=0,
        )
        await repo.add(asset)
        await db_session.flush()

        assert await repo.check_main_exists(_seed_product.id, variant_id=None) is True
        assert (
            await repo.check_main_exists(_seed_product.id, variant_id=uuid.uuid4())
            is False
        )

    async def test_bulk_update_sort_order(
        self,
        db_session: AsyncSession,
        _seed_product: Product,
    ) -> None:
        """bulk_update_sort_order changes sort_order correctly."""
        repo = MediaAssetRepository(session=db_session)
        assets = []
        for sort in [0, 1, 2]:
            asset = MediaAsset.create(
                product_id=_seed_product.id,
                media_type=MediaType.IMAGE,
                role=MediaRole.GALLERY,
                sort_order=sort,
            )
            await repo.add(asset)
            assets.append(asset)
        await db_session.flush()

        # Reverse the order
        updates = [
            (assets[0].id, 2),
            (assets[1].id, 1),
            (assets[2].id, 0),
        ]
        await repo.bulk_update_sort_order(_seed_product.id, updates)
        await db_session.flush()

        result = await repo.list_by_product(_seed_product.id)
        assert result[0].id == assets[2].id  # was sort 2, now sort 0
        assert result[2].id == assets[0].id  # was sort 0, now sort 2
