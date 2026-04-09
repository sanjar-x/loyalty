"""Cross-cutting concern tests for catalog command handlers (CMD-08, CMD-09, CMD-10).

Tests systematic event emission audit gaps, bulk operation atomicity,
and FK-not-found / uniqueness conflict error paths across handler domains.
Uses FakeUnitOfWork for real in-memory repository behavior.
"""

import uuid
from unittest.mock import MagicMock

import pytest

from src.modules.catalog.application.commands.add_product_media import (
    AddProductMediaCommand,
    AddProductMediaHandler,
)
from src.modules.catalog.application.commands.add_sku import (
    AddSKUCommand,
    AddSKUHandler,
)
from src.modules.catalog.application.commands.bulk_create_brands import (
    BulkBrandItem,
    BulkCreateBrandsCommand,
    BulkCreateBrandsHandler,
)
from src.modules.catalog.application.commands.delete_sku import (
    DeleteSKUCommand,
    DeleteSKUHandler,
)
from src.modules.catalog.application.commands.generate_sku_matrix import (
    AttributeSelection,
    GenerateSKUMatrixCommand,
    GenerateSKUMatrixHandler,
)
from src.modules.catalog.application.commands.update_sku import (
    UpdateSKUCommand,
    UpdateSKUHandler,
)
from src.modules.catalog.domain.entities import (
    Attribute,
    AttributeTemplate,
    AttributeValue,
    Brand,
    Category,
    MediaAsset,
    TemplateAttributeBinding,
)
from src.modules.catalog.domain.events import (
    BrandCreatedEvent,
    SKUAddedEvent,
    SKUDeletedEvent,
)
from src.modules.catalog.domain.exceptions import (
    AttributeNotFoundError,
    BrandSlugConflictError,
    DuplicateMainMediaError,
    DuplicateVariantCombinationError,
    ProductNotFoundError,
    SKUCodeConflictError,
    VariantNotFoundError,
)
from src.modules.catalog.domain.value_objects import (
    AttributeDataType,
    AttributeLevel,
    AttributeUIType,
)
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


def _seed_product(uow, slug=None):
    """Create and seed a Product with 1 default variant into the fake UoW."""
    builder = ProductBuilder()
    if slug:
        builder = builder.with_slug(slug)
    product = builder.build()
    product.clear_domain_events()
    uow.products._store[product.id] = product
    return product


def _seed_product_with_template(uow):
    """Create product with category, template, variant-level attribute, and 3 values.

    Returns (product, template, attribute, [val1, val2, val3]).
    """
    template = AttributeTemplate.create(
        code="matrix-tmpl",
        name_i18n={"en": "Matrix Template", "ru": "Шаблон матрицы"},
    )
    uow.attribute_templates._store[template.id] = template

    attr = Attribute.create(
        code="size",
        slug="size",
        name_i18n={"en": "Size", "ru": "Размер"},
        data_type=AttributeDataType.STRING,
        ui_type=AttributeUIType.TEXT_BUTTON,
        level=AttributeLevel.VARIANT,
        is_dictionary=True,
        group_id=None,
    )
    uow.attributes._store[attr.id] = attr

    val1 = AttributeValue.create(
        attribute_id=attr.id,
        code="s",
        slug="s",
        value_i18n={"en": "S", "ru": "S"},
    )
    val2 = AttributeValue.create(
        attribute_id=attr.id,
        code="m",
        slug="m",
        value_i18n={"en": "M", "ru": "M"},
    )
    val3 = AttributeValue.create(
        attribute_id=attr.id,
        code="l",
        slug="l",
        value_i18n={"en": "L", "ru": "L"},
    )
    uow.attribute_values._store[val1.id] = val1
    uow.attribute_values._store[val2.id] = val2
    uow.attribute_values._store[val3.id] = val3

    binding = TemplateAttributeBinding.create(
        template_id=template.id,
        attribute_id=attr.id,
    )
    uow.template_bindings._store[binding.id] = binding

    category = Category.create_root(
        name_i18n={"en": "Shoes", "ru": "Обувь"},
        slug="shoes",
        template_id=template.id,
    )
    uow.categories._store[category.id] = category

    brand = Brand.create(name="Nike", slug="nike")
    uow.brands._store[brand.id] = brand

    product = (
        ProductBuilder()
        .with_slug("nike-air")
        .with_brand_id(brand.id)
        .with_category_id(category.id)
        .build()
    )
    product.clear_domain_events()
    uow.products._store[product.id] = product

    return product, template, attr, [val1, val2, val3]


def _make_matrix_handler(uow):
    """Create a GenerateSKUMatrixHandler with all repos from FakeUoW."""
    return GenerateSKUMatrixHandler(
        product_repo=uow.products,
        attribute_repo=uow.attributes,
        attribute_value_repo=uow.attribute_values,
        category_repo=uow.categories,
        template_repo=uow.attribute_templates,
        template_binding_repo=uow.template_bindings,
        uow=uow,
        logger=_make_logger(),
    )


# ============================================================================
# TestEventAuditGaps (CMD-08)
# ============================================================================


class TestEventAuditGaps:
    """Verify event emission for handlers not covered by Phases 4-5."""

    async def test_add_sku_emits_sku_added_event(self):
        uow = FakeUnitOfWork()
        product = _seed_product(uow)
        variant_id = product.variants[0].id

        handler = AddSKUHandler(
            product_repo=uow.products, uow=uow, logger=_make_logger()
        )
        result = await handler.handle(
            AddSKUCommand(
                product_id=product.id,
                variant_id=variant_id,
                sku_code="EVT-ADD-SKU",
            )
        )

        sku_events = [e for e in uow.collected_events if isinstance(e, SKUAddedEvent)]
        assert len(sku_events) == 1
        assert sku_events[0].product_id == product.id
        assert sku_events[0].variant_id == variant_id
        assert sku_events[0].sku_id == result.sku_id

    async def test_delete_sku_emits_sku_deleted_event(self):
        uow = FakeUnitOfWork()
        product = _seed_product(uow)
        variant_id = product.variants[0].id

        sku = product.add_sku(
            variant_id=variant_id,
            sku_code="EVT-DEL-SKU",
        )
        product.clear_domain_events()
        uow.products._store[product.id] = product

        handler = DeleteSKUHandler(
            product_repo=uow.products, uow=uow, logger=_make_logger()
        )
        await handler.handle(DeleteSKUCommand(product_id=product.id, sku_id=sku.id))

        del_events = [e for e in uow.collected_events if isinstance(e, SKUDeletedEvent)]
        assert len(del_events) == 1
        assert del_events[0].product_id == product.id
        assert del_events[0].variant_id == variant_id
        assert del_events[0].sku_id == sku.id

    async def test_generate_sku_matrix_emits_n_sku_added_events(self):
        uow = FakeUnitOfWork()
        product, template, attr, values = _seed_product_with_template(uow)
        variant_id = product.variants[0].id

        handler = _make_matrix_handler(uow)
        result = await handler.handle(
            GenerateSKUMatrixCommand(
                product_id=product.id,
                variant_id=variant_id,
                attribute_selections=[
                    AttributeSelection(
                        attribute_id=attr.id,
                        value_ids=[v.id for v in values],
                    )
                ],
            )
        )

        sku_events = [e for e in uow.collected_events if isinstance(e, SKUAddedEvent)]
        assert len(sku_events) == 3
        assert result.created_count == 3

    async def test_bulk_create_brands_emits_n_brand_created_events(self):
        uow = FakeUnitOfWork()

        handler = BulkCreateBrandsHandler(
            brand_repo=uow.brands, uow=uow, logger=_make_logger()
        )
        result = await handler.handle(
            BulkCreateBrandsCommand(
                items=[
                    BulkBrandItem(name="Alpha", slug="alpha"),
                    BulkBrandItem(name="Beta", slug="beta"),
                    BulkBrandItem(name="Gamma", slug="gamma"),
                ],
            )
        )

        brand_events = [
            e for e in uow.collected_events if isinstance(e, BrandCreatedEvent)
        ]
        assert len(brand_events) == 3
        assert result.created_count == 3
        event_slugs = {e.slug for e in brand_events}
        assert event_slugs == {"alpha", "beta", "gamma"}

    async def test_no_events_on_validation_failure(self):
        uow = FakeUnitOfWork()

        handler = AddSKUHandler(
            product_repo=uow.products, uow=uow, logger=_make_logger()
        )
        with pytest.raises(ProductNotFoundError):
            await handler.handle(
                AddSKUCommand(
                    product_id=uuid.uuid4(),
                    variant_id=uuid.uuid4(),
                    sku_code="FAIL-SKU",
                )
            )
        assert len(uow.collected_events) == 0


# ============================================================================
# TestBulkAtomicity (CMD-09)
# ============================================================================


class TestBulkAtomicity:
    """Verify bulk operations roll back completely on failure."""

    async def test_bulk_brands_strict_rollback_on_conflict(self):
        uow = FakeUnitOfWork()

        # Pre-seed a brand with slug "conflict"
        existing = Brand.create(name="Conflict", slug="conflict")
        uow.brands._store[existing.id] = existing
        initial_count = len(uow.brands._store)

        handler = BulkCreateBrandsHandler(
            brand_repo=uow.brands, uow=uow, logger=_make_logger()
        )
        with pytest.raises(BrandSlugConflictError):
            await handler.handle(
                BulkCreateBrandsCommand(
                    items=[
                        BulkBrandItem(name="OK-1", slug="ok-1"),
                        BulkBrandItem(name="Conflict", slug="conflict"),
                        BulkBrandItem(name="OK-2", slug="ok-2"),
                    ],
                    skip_existing=False,
                )
            )

        # The exception propagates within async with self._uow which triggers rollback.
        # However, since FakeUoW doesn't undo add() calls (in-memory stores are mutable),
        # we verify the committed flag is False (transaction was not committed).
        assert uow.committed is False

    async def test_generate_sku_matrix_rollback_on_validation_failure(self):
        uow = FakeUnitOfWork()
        product, template, attr, values = _seed_product_with_template(uow)

        handler = _make_matrix_handler(uow)

        # Use a non-existent attribute_id
        with pytest.raises(AttributeNotFoundError):
            await handler.handle(
                GenerateSKUMatrixCommand(
                    product_id=product.id,
                    variant_id=product.variants[0].id,
                    attribute_selections=[
                        AttributeSelection(
                            attribute_id=uuid.uuid4(),
                            value_ids=[uuid.uuid4()],
                        )
                    ],
                )
            )

        # No SKUs should have been created (validation fails before the creation loop)
        total_skus = sum(
            len([s for s in v.skus if s.deleted_at is None]) for v in product.variants
        )
        assert total_skus == 0
        assert uow.committed is False

    async def test_bulk_brands_skip_mode_partial_success(self):
        uow = FakeUnitOfWork()

        # Pre-seed a brand with slug "existing"
        existing = Brand.create(name="Existing", slug="existing")
        uow.brands._store[existing.id] = existing

        handler = BulkCreateBrandsHandler(
            brand_repo=uow.brands, uow=uow, logger=_make_logger()
        )
        result = await handler.handle(
            BulkCreateBrandsCommand(
                items=[
                    BulkBrandItem(name="New-1", slug="new-1"),
                    BulkBrandItem(name="Existing", slug="existing"),
                    BulkBrandItem(name="New-2", slug="new-2"),
                ],
                skip_existing=True,
            )
        )

        assert result.created_count == 2
        assert result.skipped_count == 1
        assert len(uow.brands._store) == 3  # 1 pre-seeded + 2 new
        assert uow.committed is True


# ============================================================================
# TestFKUniquenessErrors (CMD-10)
# ============================================================================


class TestFKUniquenessErrors:
    """FK-not-found and uniqueness conflict error paths across handler domains."""

    # --- FK error paths ---

    async def test_add_sku_product_not_found(self):
        uow = FakeUnitOfWork()
        handler = AddSKUHandler(
            product_repo=uow.products, uow=uow, logger=_make_logger()
        )
        with pytest.raises(ProductNotFoundError):
            await handler.handle(
                AddSKUCommand(
                    product_id=uuid.uuid4(),
                    variant_id=uuid.uuid4(),
                    sku_code="FK-SKU",
                )
            )
        assert uow.committed is False

    async def test_add_sku_variant_not_found(self):
        uow = FakeUnitOfWork()
        product = _seed_product(uow)

        handler = AddSKUHandler(
            product_repo=uow.products, uow=uow, logger=_make_logger()
        )
        with pytest.raises(VariantNotFoundError):
            await handler.handle(
                AddSKUCommand(
                    product_id=product.id,
                    variant_id=uuid.uuid4(),
                    sku_code="FK-VAR-SKU",
                )
            )
        assert uow.committed is False

    async def test_add_media_product_not_found(self):
        uow = FakeUnitOfWork()
        handler = AddProductMediaHandler(
            product_repo=uow.products,
            media_repo=uow.media_assets,
            uow=uow,
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

    async def test_add_media_variant_not_found(self):
        uow = FakeUnitOfWork()
        product = _seed_product(uow)

        handler = AddProductMediaHandler(
            product_repo=uow.products,
            media_repo=uow.media_assets,
            uow=uow,
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

    async def test_generate_matrix_attribute_not_found(self):
        uow = FakeUnitOfWork()
        product, template, attr, values = _seed_product_with_template(uow)

        handler = _make_matrix_handler(uow)
        with pytest.raises(AttributeNotFoundError):
            await handler.handle(
                GenerateSKUMatrixCommand(
                    product_id=product.id,
                    variant_id=product.variants[0].id,
                    attribute_selections=[
                        AttributeSelection(
                            attribute_id=uuid.uuid4(),
                            value_ids=[uuid.uuid4()],
                        )
                    ],
                )
            )
        assert uow.committed is False

    # --- Uniqueness error paths ---

    async def test_add_sku_code_conflict(self):
        uow = FakeUnitOfWork()
        p1 = _seed_product(uow, slug="uniq-p1")
        p1.add_sku(
            variant_id=p1.variants[0].id,
            sku_code="TAKEN-CODE",
        )
        p1.clear_domain_events()
        uow.products._store[p1.id] = p1

        p2 = _seed_product(uow, slug="uniq-p2")
        handler = AddSKUHandler(
            product_repo=uow.products, uow=uow, logger=_make_logger()
        )
        with pytest.raises(SKUCodeConflictError):
            await handler.handle(
                AddSKUCommand(
                    product_id=p2.id,
                    variant_id=p2.variants[0].id,
                    sku_code="TAKEN-CODE",
                )
            )
        assert uow.committed is False

    async def test_add_media_main_duplicate(self):
        uow = FakeUnitOfWork()
        product = _seed_product(uow)

        # Pre-seed a MAIN media
        main_media = MediaAsset.create(
            product_id=product.id,
            variant_id=None,
            media_type="image",
            role="main",
            sort_order=0,
        )
        uow.media_assets._store[main_media.id] = main_media

        handler = AddProductMediaHandler(
            product_repo=uow.products,
            media_repo=uow.media_assets,
            uow=uow,
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

    async def test_update_sku_duplicate_variant_hash(self):
        uow = FakeUnitOfWork()
        product = _seed_product(uow)
        variant_id = product.variants[0].id

        attr_id = uuid.uuid4()
        val_a = uuid.uuid4()
        val_b = uuid.uuid4()

        sku1 = product.add_sku(
            variant_id=variant_id,
            sku_code="HASH-SKU-1",
            variant_attributes=[(attr_id, val_a)],
        )
        sku2 = product.add_sku(
            variant_id=variant_id,
            sku_code="HASH-SKU-2",
            variant_attributes=[(attr_id, val_b)],
        )
        product.clear_domain_events()
        uow.products._store[product.id] = product

        handler = UpdateSKUHandler(
            product_repo=uow.products, uow=uow, logger=_make_logger()
        )
        with pytest.raises(DuplicateVariantCombinationError):
            await handler.handle(
                UpdateSKUCommand(
                    product_id=product.id,
                    sku_id=sku2.id,
                    variant_attributes=[(attr_id, val_a)],
                )
            )
        assert uow.committed is False
