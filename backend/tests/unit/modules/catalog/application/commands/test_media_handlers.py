"""Unit tests for all Media command handlers (CMD-07).

Tests handler orchestration: product/variant ownership validation,
MAIN role uniqueness enforcement, image backend cleanup on delete,
bulk sort_order updates, and UoW commit/rollback.
Uses FakeUnitOfWork for real in-memory repository behavior.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.modules.catalog.application.commands.add_product_media import (
    AddProductMediaCommand,
    AddProductMediaHandler,
    AddProductMediaResult,
)
from src.modules.catalog.application.commands.delete_product_media import (
    DeleteProductMediaCommand,
    DeleteProductMediaHandler,
)
from src.modules.catalog.application.commands.reorder_product_media import (
    ReorderItem,
    ReorderProductMediaCommand,
    ReorderProductMediaHandler,
)
from src.modules.catalog.application.commands.update_product_media import (
    UpdateProductMediaCommand,
    UpdateProductMediaHandler,
)
from src.modules.catalog.domain.entities import MediaAsset
from src.modules.catalog.domain.exceptions import (
    DuplicateMainMediaError,
    MediaAssetNotFoundError,
    ProductNotFoundError,
    VariantNotFoundError,
)
from src.modules.catalog.domain.interfaces import IImageBackendClient
from src.modules.catalog.domain.value_objects import MediaRole
from tests.factories.product_builder import ProductBuilder
from tests.fakes.fake_uow import FakeUnitOfWork

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_logger():
    """Create a mock logger that supports .bind() chaining."""
    logger = MagicMock()
    logger.bind = MagicMock(return_value=logger)
    return logger


def _make_image_backend():
    """Create an AsyncMock for IImageBackendClient."""
    return AsyncMock(spec=IImageBackendClient)


def _seed_product(uow, slug=None):
    """Create and seed a Product with 1 default variant into the fake UoW."""
    builder = ProductBuilder()
    if slug:
        builder = builder.with_slug(slug)
    product = builder.build()
    product.clear_domain_events()
    uow.products._store[product.id] = product
    return product


def _seed_media(
    uow,
    product_id,
    variant_id=None,
    role="gallery",
    sort_order=0,
    storage_object_id=None,
):
    """Create and seed a MediaAsset into the fake UoW."""
    media = MediaAsset.create(
        product_id=product_id,
        variant_id=variant_id,
        media_type="image",
        role=role,
        sort_order=sort_order,
        storage_object_id=storage_object_id,
    )
    uow.media_assets._store[media.id] = media
    return media


# ============================================================================
# TestAddProductMedia
# ============================================================================


class TestAddProductMedia:
    """Tests for AddProductMediaHandler."""

    async def test_happy_path_gallery_image(self):
        uow = FakeUnitOfWork()
        product = _seed_product(uow)

        handler = AddProductMediaHandler(
            product_repo=uow.products,
            media_repo=uow.media_assets,
            uow=uow,
            cache=AsyncMock(),
            logger=_make_logger(),
        )
        result = await handler.handle(
            AddProductMediaCommand(
                product_id=product.id,
                media_type="image",
                role="gallery",
            )
        )

        assert isinstance(result, AddProductMediaResult)
        assert result.media_id is not None
        assert result.media_id in uow.media_assets._store
        assert uow.committed is True

    async def test_with_variant_id(self):
        uow = FakeUnitOfWork()
        product = _seed_product(uow)
        variant_id = product.variants[0].id

        handler = AddProductMediaHandler(
            product_repo=uow.products,
            media_repo=uow.media_assets,
            uow=uow,
            cache=AsyncMock(),
            logger=_make_logger(),
        )
        result = await handler.handle(
            AddProductMediaCommand(
                product_id=product.id,
                variant_id=variant_id,
                media_type="image",
                role="gallery",
            )
        )

        media = uow.media_assets._store[result.media_id]
        assert media.variant_id == variant_id
        assert uow.committed is True

    async def test_product_not_found(self):
        uow = FakeUnitOfWork()

        handler = AddProductMediaHandler(
            product_repo=uow.products,
            media_repo=uow.media_assets,
            uow=uow,
            cache=AsyncMock(),
            logger=_make_logger(),
        )
        with pytest.raises(ProductNotFoundError):
            await handler.handle(
                AddProductMediaCommand(
                    product_id=uuid.uuid4(),
                    media_type="image",
                    role="gallery",
                )
            )
        assert uow.committed is False

    async def test_variant_not_found(self):
        uow = FakeUnitOfWork()
        product = _seed_product(uow)

        handler = AddProductMediaHandler(
            product_repo=uow.products,
            media_repo=uow.media_assets,
            uow=uow,
            cache=AsyncMock(),
            logger=_make_logger(),
        )
        with pytest.raises(VariantNotFoundError):
            await handler.handle(
                AddProductMediaCommand(
                    product_id=product.id,
                    variant_id=uuid.uuid4(),
                    media_type="image",
                    role="gallery",
                )
            )
        assert uow.committed is False

    async def test_main_role_duplicate(self):
        uow = FakeUnitOfWork()
        product = _seed_product(uow)

        # Pre-seed a MAIN media for the same product+variant=None
        _seed_media(uow, product_id=product.id, variant_id=None, role="main")

        handler = AddProductMediaHandler(
            product_repo=uow.products,
            media_repo=uow.media_assets,
            uow=uow,
            cache=AsyncMock(),
            logger=_make_logger(),
        )
        with pytest.raises(DuplicateMainMediaError):
            await handler.handle(
                AddProductMediaCommand(
                    product_id=product.id,
                    media_type="image",
                    role="main",
                )
            )
        assert uow.committed is False

    async def test_main_role_different_variant_ok(self):
        uow = FakeUnitOfWork()
        product = _seed_product(uow)
        variant_id = product.variants[0].id

        # Pre-seed MAIN for variant_id=None
        _seed_media(uow, product_id=product.id, variant_id=None, role="main")

        handler = AddProductMediaHandler(
            product_repo=uow.products,
            media_repo=uow.media_assets,
            uow=uow,
            cache=AsyncMock(),
            logger=_make_logger(),
        )
        # Adding MAIN for a specific variant should succeed (different scope)
        result = await handler.handle(
            AddProductMediaCommand(
                product_id=product.id,
                variant_id=variant_id,
                media_type="image",
                role="main",
            )
        )

        assert result.media_id is not None
        assert uow.committed is True


# ============================================================================
# TestUpdateProductMedia
# ============================================================================


class TestUpdateProductMedia:
    """Tests for UpdateProductMediaHandler."""

    async def test_happy_path_update_sort_order(self):
        uow = FakeUnitOfWork()
        product = _seed_product(uow)
        media = _seed_media(uow, product_id=product.id, sort_order=0)

        handler = UpdateProductMediaHandler(
            product_repo=uow.products,
            media_repo=uow.media_assets,
            uow=uow,
            cache=AsyncMock(),
            logger=_make_logger(),
        )
        result = await handler.handle(
            UpdateProductMediaCommand(
                product_id=product.id,
                media_id=media.id,
                sort_order=5,
                _provided_fields=frozenset({"sort_order"}),
            )
        )

        assert result.id == media.id
        assert media.sort_order == 5
        assert uow.committed is True

    async def test_happy_path_update_role(self):
        uow = FakeUnitOfWork()
        product = _seed_product(uow)
        media = _seed_media(uow, product_id=product.id, role="gallery")

        handler = UpdateProductMediaHandler(
            product_repo=uow.products,
            media_repo=uow.media_assets,
            uow=uow,
            cache=AsyncMock(),
            logger=_make_logger(),
        )
        await handler.handle(
            UpdateProductMediaCommand(
                product_id=product.id,
                media_id=media.id,
                role="main",
                _provided_fields=frozenset({"role"}),
            )
        )

        assert media.role == MediaRole.MAIN
        assert uow.committed is True

    async def test_media_not_found(self):
        uow = FakeUnitOfWork()

        handler = UpdateProductMediaHandler(
            product_repo=uow.products,
            media_repo=uow.media_assets,
            uow=uow,
            cache=AsyncMock(),
            logger=_make_logger(),
        )
        with pytest.raises(MediaAssetNotFoundError):
            await handler.handle(
                UpdateProductMediaCommand(
                    product_id=uuid.uuid4(),
                    media_id=uuid.uuid4(),
                    sort_order=1,
                    _provided_fields=frozenset({"sort_order"}),
                )
            )
        assert uow.committed is False

    async def test_ownership_mismatch(self):
        uow = FakeUnitOfWork()
        product = _seed_product(uow, slug="owner-product")
        media = _seed_media(uow, product_id=product.id)

        handler = UpdateProductMediaHandler(
            product_repo=uow.products,
            media_repo=uow.media_assets,
            uow=uow,
            cache=AsyncMock(),
            logger=_make_logger(),
        )
        # Use a different product_id for the command
        with pytest.raises(MediaAssetNotFoundError):
            await handler.handle(
                UpdateProductMediaCommand(
                    product_id=uuid.uuid4(),
                    media_id=media.id,
                    sort_order=1,
                    _provided_fields=frozenset({"sort_order"}),
                )
            )
        assert uow.committed is False

    async def test_main_role_conflict(self):
        uow = FakeUnitOfWork()
        product = _seed_product(uow)

        # Pre-seed existing MAIN media
        _seed_media(uow, product_id=product.id, variant_id=None, role="main")
        # Another gallery media we want to update to MAIN
        media = _seed_media(uow, product_id=product.id, variant_id=None, role="gallery")

        handler = UpdateProductMediaHandler(
            product_repo=uow.products,
            media_repo=uow.media_assets,
            uow=uow,
            cache=AsyncMock(),
            logger=_make_logger(),
        )
        with pytest.raises(DuplicateMainMediaError):
            await handler.handle(
                UpdateProductMediaCommand(
                    product_id=product.id,
                    media_id=media.id,
                    role="main",
                    _provided_fields=frozenset({"role"}),
                )
            )
        assert uow.committed is False

    async def test_variant_not_found_on_change(self):
        uow = FakeUnitOfWork()
        product = _seed_product(uow)
        media = _seed_media(uow, product_id=product.id, variant_id=None)

        handler = UpdateProductMediaHandler(
            product_repo=uow.products,
            media_repo=uow.media_assets,
            uow=uow,
            cache=AsyncMock(),
            logger=_make_logger(),
        )
        with pytest.raises(VariantNotFoundError):
            await handler.handle(
                UpdateProductMediaCommand(
                    product_id=product.id,
                    media_id=media.id,
                    variant_id=uuid.uuid4(),
                    _provided_fields=frozenset({"variant_id"}),
                )
            )
        assert uow.committed is False


# ============================================================================
# TestDeleteProductMedia
# ============================================================================


class TestDeleteProductMedia:
    """Tests for DeleteProductMediaHandler."""

    async def test_happy_path_deletes_and_cleans_up(self):
        uow = FakeUnitOfWork()
        product = _seed_product(uow)
        storage_id = uuid.uuid4()
        media = _seed_media(uow, product_id=product.id, storage_object_id=storage_id)
        image_backend = _make_image_backend()

        handler = DeleteProductMediaHandler(
            media_repo=uow.media_assets,
            uow=uow,
            image_backend=image_backend,
            logger=_make_logger(),
        )
        await handler.handle(
            DeleteProductMediaCommand(
                product_id=product.id,
                media_id=media.id,
            )
        )

        assert media.id not in uow.media_assets._store
        assert uow.committed is True
        image_backend.delete.assert_called_once_with(storage_id)

    async def test_no_cleanup_when_no_storage_object(self):
        uow = FakeUnitOfWork()
        product = _seed_product(uow)
        media = _seed_media(uow, product_id=product.id, storage_object_id=None)
        image_backend = _make_image_backend()

        handler = DeleteProductMediaHandler(
            media_repo=uow.media_assets,
            uow=uow,
            image_backend=image_backend,
            logger=_make_logger(),
        )
        await handler.handle(
            DeleteProductMediaCommand(
                product_id=product.id,
                media_id=media.id,
            )
        )

        assert uow.committed is True
        image_backend.delete.assert_not_called()

    async def test_media_not_found(self):
        uow = FakeUnitOfWork()
        image_backend = _make_image_backend()

        handler = DeleteProductMediaHandler(
            media_repo=uow.media_assets,
            uow=uow,
            image_backend=image_backend,
            logger=_make_logger(),
        )
        with pytest.raises(MediaAssetNotFoundError):
            await handler.handle(
                DeleteProductMediaCommand(
                    product_id=uuid.uuid4(),
                    media_id=uuid.uuid4(),
                )
            )
        assert uow.committed is False

    async def test_ownership_mismatch(self):
        uow = FakeUnitOfWork()
        product = _seed_product(uow)
        media = _seed_media(uow, product_id=product.id)
        image_backend = _make_image_backend()

        handler = DeleteProductMediaHandler(
            media_repo=uow.media_assets,
            uow=uow,
            image_backend=image_backend,
            logger=_make_logger(),
        )
        with pytest.raises(MediaAssetNotFoundError):
            await handler.handle(
                DeleteProductMediaCommand(
                    product_id=uuid.uuid4(),
                    media_id=media.id,
                )
            )
        assert uow.committed is False

    async def test_cleanup_after_commit_not_before(self):
        """Verify image_backend.delete is called AFTER uow.commit."""
        uow = FakeUnitOfWork()
        product = _seed_product(uow)
        storage_id = uuid.uuid4()
        media = _seed_media(uow, product_id=product.id, storage_object_id=storage_id)

        call_order = []
        original_commit = uow.commit

        async def tracking_commit():
            await original_commit()
            call_order.append("commit")

        uow.commit = tracking_commit  # ty: ignore[invalid-assignment]

        image_backend = _make_image_backend()

        async def tracking_delete(sid):
            call_order.append("delete")

        image_backend.delete = tracking_delete

        handler = DeleteProductMediaHandler(
            media_repo=uow.media_assets,
            uow=uow,
            image_backend=image_backend,
            logger=_make_logger(),
        )
        await handler.handle(
            DeleteProductMediaCommand(
                product_id=product.id,
                media_id=media.id,
            )
        )

        assert call_order == ["commit", "delete"]


# ============================================================================
# TestReorderProductMedia
# ============================================================================


class TestReorderProductMedia:
    """Tests for ReorderProductMediaHandler."""

    async def test_happy_path_reorders(self):
        uow = FakeUnitOfWork()
        product = _seed_product(uow)

        m1 = _seed_media(uow, product_id=product.id, sort_order=0)
        m2 = _seed_media(uow, product_id=product.id, sort_order=1)
        m3 = _seed_media(uow, product_id=product.id, sort_order=2)

        handler = ReorderProductMediaHandler(
            media_repo=uow.media_assets,
            product_repo=uow.products,
            uow=uow,
            cache=AsyncMock(),
            logger=_make_logger(),
        )
        await handler.handle(
            ReorderProductMediaCommand(
                product_id=product.id,
                items=[
                    ReorderItem(media_id=m1.id, sort_order=2),
                    ReorderItem(media_id=m2.id, sort_order=0),
                    ReorderItem(media_id=m3.id, sort_order=1),
                ],
            )
        )

        assert m1.sort_order == 2
        assert m2.sort_order == 0
        assert m3.sort_order == 1
        assert uow.committed is True

    async def test_partial_match_raises_error(self):
        uow = FakeUnitOfWork()
        product = _seed_product(uow)

        m1 = _seed_media(uow, product_id=product.id, sort_order=0)
        m2 = _seed_media(uow, product_id=product.id, sort_order=1)

        handler = ReorderProductMediaHandler(
            media_repo=uow.media_assets,
            product_repo=uow.products,
            uow=uow,
            cache=AsyncMock(),
            logger=_make_logger(),
        )
        # Third item has a non-existent media_id
        with pytest.raises(MediaAssetNotFoundError):
            await handler.handle(
                ReorderProductMediaCommand(
                    product_id=product.id,
                    items=[
                        ReorderItem(media_id=m1.id, sort_order=1),
                        ReorderItem(media_id=m2.id, sort_order=0),
                        ReorderItem(media_id=uuid.uuid4(), sort_order=2),
                    ],
                )
            )
        assert uow.committed is False

    async def test_empty_items(self):
        uow = FakeUnitOfWork()
        product = _seed_product(uow)

        handler = ReorderProductMediaHandler(
            media_repo=uow.media_assets,
            product_repo=uow.products,
            uow=uow,
            cache=AsyncMock(),
            logger=_make_logger(),
        )
        # Empty items list -> should still commit (0 updated == 0 expected)
        await handler.handle(
            ReorderProductMediaCommand(
                product_id=product.id,
                items=[],
            )
        )
        assert uow.committed is True
