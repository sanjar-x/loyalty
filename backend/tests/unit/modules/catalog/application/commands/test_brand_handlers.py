"""Unit tests for Brand command handlers (CMD-01).

Tests all 4 Brand command handlers:
- CreateBrandHandler
- UpdateBrandHandler
- DeleteBrandHandler
- BulkCreateBrandsHandler

Per D-01: one test class per handler.
Per D-02: one test file per entity domain.
Per D-03: uses FakeUnitOfWork for all repository interactions.
Per D-07: asserts uow.committed on happy path, uow.committed is False on rejection.
Per D-08: asserts events via uow.collected_events (not entity.domain_events).
"""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.modules.catalog.application.commands.bulk_create_brands import (
    BulkBrandItem,
    BulkCreateBrandsCommand,
    BulkCreateBrandsHandler,
)
from src.modules.catalog.application.commands.create_brand import (
    CreateBrandCommand,
    CreateBrandHandler,
)
from src.modules.catalog.application.commands.delete_brand import (
    DeleteBrandCommand,
    DeleteBrandHandler,
)
from src.modules.catalog.application.commands.update_brand import (
    UpdateBrandCommand,
    UpdateBrandHandler,
)
from src.modules.catalog.domain.events import (
    BrandCreatedEvent,
    BrandDeletedEvent,
    BrandUpdatedEvent,
)
from src.modules.catalog.domain.exceptions import (
    BrandHasProductsError,
    BrandNameConflictError,
    BrandNotFoundError,
    BrandSlugConflictError,
)
from src.shared.exceptions import ValidationError
from tests.factories.brand_builder import BrandBuilder
from tests.factories.product_builder import ProductBuilder
from tests.fakes.fake_uow import FakeUnitOfWork


def make_logger():
    """Create a mock logger that supports .bind() chaining."""
    logger = MagicMock()
    logger.bind = MagicMock(return_value=logger)
    return logger


def make_image_backend():
    """AsyncMock for IImageBackendClient (needed by UpdateBrandHandler)."""
    return AsyncMock()


# ============================================================================
# TestCreateBrand
# ============================================================================


class TestCreateBrand:
    """Tests for CreateBrandHandler."""

    async def test_creates_brand_and_commits(self):
        uow = FakeUnitOfWork()
        handler = CreateBrandHandler(
            brand_repo=uow.brands,
            uow=uow,
            logger=make_logger(),
        )

        result = await handler.handle(CreateBrandCommand(name="Nike", slug="nike"))

        assert uow.committed is True
        assert result.brand_id in uow.brands._store

    async def test_rejects_duplicate_slug(self):
        uow = FakeUnitOfWork()
        existing = BrandBuilder().with_slug("nike").build()
        uow.brands._store[existing.id] = existing

        handler = CreateBrandHandler(
            brand_repo=uow.brands,
            uow=uow,
            logger=make_logger(),
        )

        with pytest.raises(BrandSlugConflictError):
            await handler.handle(CreateBrandCommand(name="Nike New", slug="nike"))

        assert uow.committed is False

    async def test_emits_brand_created_event(self):
        uow = FakeUnitOfWork()
        handler = CreateBrandHandler(
            brand_repo=uow.brands,
            uow=uow,
            logger=make_logger(),
        )

        await handler.handle(CreateBrandCommand(name="Adidas", slug="adidas"))

        assert len(uow.collected_events) == 1
        assert isinstance(uow.collected_events[0], BrandCreatedEvent)

    async def test_stores_logo_fields(self):
        uow = FakeUnitOfWork()
        handler = CreateBrandHandler(
            brand_repo=uow.brands,
            uow=uow,
            logger=make_logger(),
        )
        storage_id = uuid.uuid4()

        result = await handler.handle(
            CreateBrandCommand(
                name="Puma",
                slug="puma",
                logo_url="https://example.com/logo.png",
                logo_storage_object_id=storage_id,
            )
        )

        brand = uow.brands._store[result.brand_id]
        assert brand.logo_url == "https://example.com/logo.png"
        assert brand.logo_storage_object_id == storage_id


# ============================================================================
# TestUpdateBrand
# ============================================================================


class TestUpdateBrand:
    """Tests for UpdateBrandHandler.

    CRITICAL: Every UpdateBrandCommand MUST include _provided_fields frozenset.
    CRITICAL: UpdateBrandHandler requires image_backend (IImageBackendClient).
    """

    async def test_updates_name_and_commits(self):
        uow = FakeUnitOfWork()
        brand = BrandBuilder().with_name("Old Name").with_slug("old-name").build()
        uow.brands._store[brand.id] = brand

        handler = UpdateBrandHandler(
            brand_repo=uow.brands,
            uow=uow,
            image_backend=make_image_backend(),
            logger=make_logger(),
        )

        result = await handler.handle(
            UpdateBrandCommand(
                brand_id=brand.id,
                name="New Name",
                _provided_fields=frozenset({"name"}),
            )
        )

        assert result.name == "New Name"
        assert uow.committed is True

    async def test_rejects_not_found(self):
        uow = FakeUnitOfWork()
        handler = UpdateBrandHandler(
            brand_repo=uow.brands,
            uow=uow,
            image_backend=make_image_backend(),
            logger=make_logger(),
        )

        with pytest.raises(BrandNotFoundError):
            await handler.handle(
                UpdateBrandCommand(
                    brand_id=uuid.uuid4(),
                    name="Whatever",
                    _provided_fields=frozenset({"name"}),
                )
            )

        assert uow.committed is False

    async def test_rejects_duplicate_slug(self):
        uow = FakeUnitOfWork()
        brand_a = BrandBuilder().with_name("Brand A").with_slug("brand-a").build()
        brand_b = BrandBuilder().with_name("Brand B").with_slug("brand-b").build()
        uow.brands._store[brand_a.id] = brand_a
        uow.brands._store[brand_b.id] = brand_b

        handler = UpdateBrandHandler(
            brand_repo=uow.brands,
            uow=uow,
            image_backend=make_image_backend(),
            logger=make_logger(),
        )

        with pytest.raises(BrandSlugConflictError):
            await handler.handle(
                UpdateBrandCommand(
                    brand_id=brand_a.id,
                    slug="brand-b",
                    _provided_fields=frozenset({"slug"}),
                )
            )

        assert uow.committed is False

    async def test_emits_brand_updated_event(self):
        uow = FakeUnitOfWork()
        brand = BrandBuilder().with_name("Reebok").with_slug("reebok").build()
        uow.brands._store[brand.id] = brand

        handler = UpdateBrandHandler(
            brand_repo=uow.brands,
            uow=uow,
            image_backend=make_image_backend(),
            logger=make_logger(),
        )

        await handler.handle(
            UpdateBrandCommand(
                brand_id=brand.id,
                name="Reebok Classic",
                _provided_fields=frozenset({"name"}),
            )
        )

        assert len(uow.collected_events) == 1
        assert isinstance(uow.collected_events[0], BrandUpdatedEvent)

    async def test_logo_change_triggers_cleanup(self):
        uow = FakeUnitOfWork()
        old_storage_id = uuid.uuid4()
        new_storage_id = uuid.uuid4()

        brand = (
            BrandBuilder()
            .with_name("Logo Brand")
            .with_slug("logo-brand")
            .with_logo("https://old.com/logo.png", old_storage_id)
            .build()
        )
        uow.brands._store[brand.id] = brand

        image_backend = make_image_backend()
        handler = UpdateBrandHandler(
            brand_repo=uow.brands,
            uow=uow,
            image_backend=image_backend,
            logger=make_logger(),
        )

        await handler.handle(
            UpdateBrandCommand(
                brand_id=brand.id,
                logo_url="https://new.com/logo.png",
                logo_storage_object_id=new_storage_id,
                _provided_fields=frozenset({"logo_url", "logo_storage_object_id"}),
            )
        )

        image_backend.delete.assert_called_once_with(old_storage_id)


# ============================================================================
# TestDeleteBrand
# ============================================================================


class TestDeleteBrand:
    """Tests for DeleteBrandHandler."""

    async def test_deletes_brand_and_commits(self):
        uow = FakeUnitOfWork()
        brand = BrandBuilder().with_slug("delete-me").build()
        uow.brands._store[brand.id] = brand

        handler = DeleteBrandHandler(
            brand_repo=uow.brands,
            uow=uow,
            logger=make_logger(),
        )

        await handler.handle(DeleteBrandCommand(brand_id=brand.id))

        assert brand.id not in uow.brands._store
        assert uow.committed is True

    async def test_rejects_not_found(self):
        uow = FakeUnitOfWork()
        handler = DeleteBrandHandler(
            brand_repo=uow.brands,
            uow=uow,
            logger=make_logger(),
        )

        with pytest.raises(BrandNotFoundError):
            await handler.handle(DeleteBrandCommand(brand_id=uuid.uuid4()))

        assert uow.committed is False

    async def test_rejects_has_products(self):
        uow = FakeUnitOfWork()
        brand = BrandBuilder().with_slug("has-products").build()
        uow.brands._store[brand.id] = brand

        product = ProductBuilder().with_brand_id(brand.id).build()
        uow.products._store[product.id] = product

        handler = DeleteBrandHandler(
            brand_repo=uow.brands,
            uow=uow,
            logger=make_logger(),
        )

        with pytest.raises(BrandHasProductsError):
            await handler.handle(DeleteBrandCommand(brand_id=brand.id))

        assert uow.committed is False

    async def test_emits_brand_deleted_event(self):
        uow = FakeUnitOfWork()
        brand = BrandBuilder().with_slug("event-brand").build()
        uow.brands._store[brand.id] = brand

        handler = DeleteBrandHandler(
            brand_repo=uow.brands,
            uow=uow,
            logger=make_logger(),
        )

        await handler.handle(DeleteBrandCommand(brand_id=brand.id))

        assert len(uow.collected_events) == 1
        assert isinstance(uow.collected_events[0], BrandDeletedEvent)


# ============================================================================
# TestBulkCreateBrands
# ============================================================================


class TestBulkCreateBrands:
    """Tests for BulkCreateBrandsHandler.

    Per Pitfall 7: tests BOTH slug AND name uniqueness.
    """

    async def test_creates_multiple_brands(self):
        uow = FakeUnitOfWork()
        handler = BulkCreateBrandsHandler(
            brand_repo=uow.brands,
            uow=uow,
            logger=make_logger(),
        )

        result = await handler.handle(
            BulkCreateBrandsCommand(
                items=[
                    BulkBrandItem(name="Nike", slug="nike"),
                    BulkBrandItem(name="Adidas", slug="adidas"),
                    BulkBrandItem(name="Puma", slug="puma"),
                ]
            )
        )

        assert result.created_count == 3
        assert len(result.ids) == 3
        for brand_id in result.ids:
            assert brand_id in uow.brands._store

    async def test_skip_existing_mode(self):
        uow = FakeUnitOfWork()
        existing = BrandBuilder().with_name("Existing").with_slug("existing").build()
        uow.brands._store[existing.id] = existing

        handler = BulkCreateBrandsHandler(
            brand_repo=uow.brands,
            uow=uow,
            logger=make_logger(),
        )

        result = await handler.handle(
            BulkCreateBrandsCommand(
                items=[
                    BulkBrandItem(name="Existing", slug="existing"),
                    BulkBrandItem(name="New Brand", slug="new-brand"),
                ],
                skip_existing=True,
            )
        )

        assert result.skipped_count == 1
        assert result.skipped_slugs == ["existing"]
        assert result.created_count == 1

    async def test_strict_mode_rejects_slug_conflict(self):
        uow = FakeUnitOfWork()
        existing = BrandBuilder().with_name("Existing").with_slug("existing").build()
        uow.brands._store[existing.id] = existing

        handler = BulkCreateBrandsHandler(
            brand_repo=uow.brands,
            uow=uow,
            logger=make_logger(),
        )

        with pytest.raises(BrandSlugConflictError):
            await handler.handle(
                BulkCreateBrandsCommand(
                    items=[
                        BulkBrandItem(name="Another Name", slug="existing"),
                    ]
                )
            )

        assert uow.committed is False

    async def test_strict_mode_rejects_name_conflict(self):
        uow = FakeUnitOfWork()
        existing = BrandBuilder().with_name("Existing").with_slug("existing").build()
        uow.brands._store[existing.id] = existing

        handler = BulkCreateBrandsHandler(
            brand_repo=uow.brands,
            uow=uow,
            logger=make_logger(),
        )

        with pytest.raises(BrandNameConflictError):
            await handler.handle(
                BulkCreateBrandsCommand(
                    items=[
                        BulkBrandItem(name="Existing", slug="different-slug"),
                    ]
                )
            )

        assert uow.committed is False

    async def test_rejects_batch_limit_exceeded(self):
        uow = FakeUnitOfWork()
        handler = BulkCreateBrandsHandler(
            brand_repo=uow.brands,
            uow=uow,
            logger=make_logger(),
        )

        items = [
            BulkBrandItem(name=f"Brand {i}", slug=f"brand-{i}") for i in range(101)
        ]

        with pytest.raises(ValidationError) as exc_info:
            await handler.handle(BulkCreateBrandsCommand(items=items))

        assert exc_info.value.error_code == "BULK_LIMIT_EXCEEDED"

    async def test_rejects_duplicate_slugs_in_batch(self):
        uow = FakeUnitOfWork()
        handler = BulkCreateBrandsHandler(
            brand_repo=uow.brands,
            uow=uow,
            logger=make_logger(),
        )

        with pytest.raises(ValidationError) as exc_info:
            await handler.handle(
                BulkCreateBrandsCommand(
                    items=[
                        BulkBrandItem(name="Brand A", slug="same-slug"),
                        BulkBrandItem(name="Brand B", slug="same-slug"),
                    ]
                )
            )

        assert exc_info.value.error_code == "BULK_DUPLICATE_SLUGS"

    async def test_rejects_duplicate_names_in_batch(self):
        uow = FakeUnitOfWork()
        handler = BulkCreateBrandsHandler(
            brand_repo=uow.brands,
            uow=uow,
            logger=make_logger(),
        )

        with pytest.raises(ValidationError) as exc_info:
            await handler.handle(
                BulkCreateBrandsCommand(
                    items=[
                        BulkBrandItem(name="Same Name", slug="slug-a"),
                        BulkBrandItem(name="Same Name", slug="slug-b"),
                    ]
                )
            )

        assert exc_info.value.error_code == "BULK_DUPLICATE_NAMES"

    async def test_emits_events_for_each_created(self):
        uow = FakeUnitOfWork()
        handler = BulkCreateBrandsHandler(
            brand_repo=uow.brands,
            uow=uow,
            logger=make_logger(),
        )

        await handler.handle(
            BulkCreateBrandsCommand(
                items=[
                    BulkBrandItem(name="Brand X", slug="brand-x"),
                    BulkBrandItem(name="Brand Y", slug="brand-y"),
                ]
            )
        )

        assert len(uow.collected_events) == 2
        assert all(isinstance(e, BrandCreatedEvent) for e in uow.collected_events)
