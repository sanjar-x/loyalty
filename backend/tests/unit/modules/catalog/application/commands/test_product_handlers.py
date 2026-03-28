"""Unit tests for all Product command handlers (CMD-04).

Tests handler orchestration: repository interactions, UoW commit/rollback,
domain exception propagation, and cross-module dependency mocking.
Uses FakeUnitOfWork for real in-memory repository behavior (D-08).
"""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.modules.catalog.application.commands.assign_product_attribute import (
    AssignProductAttributeCommand,
    AssignProductAttributeHandler,
    AssignProductAttributeResult,
)
from src.modules.catalog.application.commands.bulk_assign_product_attributes import (
    AttributeAssignmentItem,
    BulkAssignProductAttributesCommand,
    BulkAssignProductAttributesHandler,
    BulkAssignProductAttributesResult,
)
from src.modules.catalog.application.commands.change_product_status import (
    ChangeProductStatusCommand,
    ChangeProductStatusHandler,
)
from src.modules.catalog.application.commands.create_product import (
    CreateProductCommand,
    CreateProductHandler,
    CreateProductResult,
)
from src.modules.catalog.application.commands.delete_product import (
    DeleteProductCommand,
    DeleteProductHandler,
)
from src.modules.catalog.application.commands.delete_product_attribute import (
    DeleteProductAttributeCommand,
    DeleteProductAttributeHandler,
)
from src.modules.catalog.application.commands.update_product import (
    UpdateProductCommand,
    UpdateProductHandler,
    UpdateProductResult,
)
from src.modules.catalog.domain.entities import (
    Attribute,
    AttributeGroup,
    AttributeTemplate,
    AttributeValue,
    Brand,
    Category,
    MediaAsset,
    Product,
    ProductAttributeValue,
    TemplateAttributeBinding,
)
from src.modules.catalog.domain.exceptions import (
    AttributeLevelMismatchError,
    AttributeNotDictionaryError,
    AttributeNotFoundError,
    AttributeNotInTemplateError,
    AttributeValueNotFoundError,
    BrandNotFoundError,
    CategoryNotFoundError,
    ConcurrencyError,
    DuplicateProductAttributeError,
    InvalidStatusTransitionError,
    ProductAttributeValueNotFoundError,
    ProductNotFoundError,
    ProductNotReadyError,
    ProductSlugConflictError,
)
from src.modules.catalog.domain.interfaces import IImageBackendClient
from src.modules.catalog.domain.value_objects import (
    AttributeDataType,
    AttributeLevel,
    AttributeUIType,  # TEXT_BUTTON, COLOR_SWATCH, DROPDOWN, CHECKBOX, RANGE_SLIDER
    ProductStatus,
)
from src.modules.supplier.domain.exceptions import (
    SourceUrlRequiredError,
    SupplierInactiveError,
)
from src.modules.supplier.domain.interfaces import ISupplierQueryService, SupplierInfo
from src.modules.supplier.domain.value_objects import SupplierType
from src.shared.exceptions import UnprocessableEntityError
from src.shared.interfaces.logger import ILogger
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


def _make_supplier_service(
    supplier_info=None,
    raises=None,
):
    """Create an AsyncMock supplier query service."""
    svc = AsyncMock(spec=ISupplierQueryService)
    if raises:
        svc.assert_supplier_active.side_effect = raises
    elif supplier_info:
        svc.assert_supplier_active.return_value = supplier_info
    return svc


def _make_image_backend():
    """Create an AsyncMock image backend client."""
    return AsyncMock(spec=IImageBackendClient)


def _seed_brand(uow, slug="nike", name="Nike"):
    """Create and seed a Brand into the fake UoW."""
    brand = Brand.create(name=name, slug=slug)
    uow.brands._store[brand.id] = brand
    return brand


def _seed_category(uow, slug="shoes", template_id=None):
    """Create and seed a root Category into the fake UoW."""
    cat = Category.create_root(
        name_i18n={"en": "Shoes", "ru": "Обувь"},
        slug=slug,
        template_id=template_id,
    )
    uow.categories._store[cat.id] = cat
    return cat


def _seed_product(uow, brand_id=None, category_id=None, slug=None):
    """Create and seed a Product into the fake UoW."""
    builder = ProductBuilder()
    if brand_id:
        builder = builder.with_brand_id(brand_id)
    if category_id:
        builder = builder.with_category_id(category_id)
    if slug:
        builder = builder.with_slug(slug)
    product = builder.build()
    uow.products._store[product.id] = product
    return product


def _seed_attribute_group(uow):
    """Create and seed an AttributeGroup into the fake UoW."""
    group = AttributeGroup.create(
        code="general",
        name_i18n={"en": "General", "ru": "Общие"},
    )
    uow.attribute_groups._store[group.id] = group
    return group


def _seed_attribute(uow, group_id, level=AttributeLevel.PRODUCT, is_dictionary=True):
    """Create and seed an Attribute into the fake UoW."""
    attr = Attribute.create(
        code="color",
        slug="color",
        name_i18n={"en": "Color", "ru": "Цвет"},
        data_type=AttributeDataType.STRING,
        ui_type=AttributeUIType.DROPDOWN,
        is_dictionary=is_dictionary,
        group_id=group_id,
        level=level,
    )
    uow.attributes._store[attr.id] = attr
    return attr


def _seed_attribute_value(uow, attribute_id):
    """Create and seed an AttributeValue into the fake UoW."""
    val = AttributeValue.create(
        attribute_id=attribute_id,
        code="red",
        slug="red",
        value_i18n={"en": "Red", "ru": "Красный"},
    )
    uow.attribute_values._store[val.id] = val
    return val


def _seed_template(uow):
    """Create and seed an AttributeTemplate into the fake UoW."""
    tmpl = AttributeTemplate.create(
        code="shoes-template",
        name_i18n={"en": "Shoes Template", "ru": "Шаблон обуви"},
    )
    uow.attribute_templates._store[tmpl.id] = tmpl
    return tmpl


def _seed_binding(uow, template_id, attribute_id):
    """Create and seed a TemplateAttributeBinding into the fake UoW."""
    binding = TemplateAttributeBinding.create(
        template_id=template_id,
        attribute_id=attribute_id,
    )
    uow.template_bindings._store[binding.id] = binding
    return binding


def _seed_media_asset(uow, product_id, variant_id=None):
    """Create and seed a MediaAsset into the fake UoW."""
    media = MediaAsset.create(
        product_id=product_id,
        variant_id=variant_id,
        media_type="IMAGE",
        role="GALLERY",
        sort_order=0,
        storage_object_id=uuid.uuid4(),
    )
    uow.media_assets._store[media.id] = media
    return media


# ============================================================================
# TestCreateProduct
# ============================================================================


class TestCreateProduct:
    """Tests for CreateProductHandler."""

    async def test_happy_path_no_supplier(self):
        uow = FakeUnitOfWork()
        brand = _seed_brand(uow)
        cat = _seed_category(uow)
        svc = _make_supplier_service()

        handler = CreateProductHandler(
            product_repo=uow.products,
            brand_repo=uow.brands,
            category_repo=uow.categories,
            supplier_query_service=svc,
            media_repo=uow.media_assets,
            uow=uow,
            logger=_make_logger(),
        )

        result = await handler.handle(
            CreateProductCommand(
                title_i18n={"en": "Air Max", "ru": "Эйр Макс"},
                slug="air-max",
                brand_id=brand.id,
                primary_category_id=cat.id,
            )
        )

        assert isinstance(result, CreateProductResult)
        assert result.product_id in uow.products._store
        assert result.default_variant_id is not None
        assert uow.committed is True
        svc.assert_supplier_active.assert_not_awaited()

    async def test_happy_path_local_supplier(self):
        uow = FakeUnitOfWork()
        brand = _seed_brand(uow)
        cat = _seed_category(uow)
        supplier_id = uuid.uuid4()
        info = SupplierInfo(
            id=supplier_id,
            name="Local Store",
            type=SupplierType.LOCAL,
            is_active=True,
        )
        svc = _make_supplier_service(supplier_info=info)

        handler = CreateProductHandler(
            product_repo=uow.products,
            brand_repo=uow.brands,
            category_repo=uow.categories,
            supplier_query_service=svc,
            media_repo=uow.media_assets,
            uow=uow,
            logger=_make_logger(),
        )

        result = await handler.handle(
            CreateProductCommand(
                title_i18n={"en": "Air Max", "ru": "Эйр Макс"},
                slug="air-max",
                brand_id=brand.id,
                primary_category_id=cat.id,
                supplier_id=supplier_id,
            )
        )

        assert uow.committed is True
        assert result.product_id in uow.products._store

    async def test_happy_path_cross_border_with_source_url(self):
        uow = FakeUnitOfWork()
        brand = _seed_brand(uow)
        cat = _seed_category(uow)
        supplier_id = uuid.uuid4()
        info = SupplierInfo(
            id=supplier_id,
            name="Poizon",
            type=SupplierType.CROSS_BORDER,
            is_active=True,
        )
        svc = _make_supplier_service(supplier_info=info)

        handler = CreateProductHandler(
            product_repo=uow.products,
            brand_repo=uow.brands,
            category_repo=uow.categories,
            supplier_query_service=svc,
            media_repo=uow.media_assets,
            uow=uow,
            logger=_make_logger(),
        )

        result = await handler.handle(
            CreateProductCommand(
                title_i18n={"en": "Air Max", "ru": "Эйр Макс"},
                slug="air-max",
                brand_id=brand.id,
                primary_category_id=cat.id,
                supplier_id=supplier_id,
                source_url="https://dw4.co/t/abc",
            )
        )

        assert uow.committed is True
        assert result.product_id in uow.products._store

    async def test_brand_not_found(self):
        uow = FakeUnitOfWork()
        _seed_category(uow)
        svc = _make_supplier_service()

        handler = CreateProductHandler(
            product_repo=uow.products,
            brand_repo=uow.brands,
            category_repo=uow.categories,
            supplier_query_service=svc,
            media_repo=uow.media_assets,
            uow=uow,
            logger=_make_logger(),
        )

        with pytest.raises(BrandNotFoundError):
            await handler.handle(
                CreateProductCommand(
                    title_i18n={"en": "Air Max", "ru": "Эйр Макс"},
                    slug="air-max",
                    brand_id=uuid.uuid4(),
                    primary_category_id=uuid.uuid4(),
                )
            )

        assert uow.committed is False

    async def test_category_not_found(self):
        uow = FakeUnitOfWork()
        brand = _seed_brand(uow)
        svc = _make_supplier_service()

        handler = CreateProductHandler(
            product_repo=uow.products,
            brand_repo=uow.brands,
            category_repo=uow.categories,
            supplier_query_service=svc,
            media_repo=uow.media_assets,
            uow=uow,
            logger=_make_logger(),
        )

        with pytest.raises(CategoryNotFoundError):
            await handler.handle(
                CreateProductCommand(
                    title_i18n={"en": "Air Max", "ru": "Эйр Макс"},
                    slug="air-max",
                    brand_id=brand.id,
                    primary_category_id=uuid.uuid4(),
                )
            )

        assert uow.committed is False

    async def test_slug_conflict(self):
        uow = FakeUnitOfWork()
        brand = _seed_brand(uow)
        cat = _seed_category(uow)
        _seed_product(uow, brand_id=brand.id, category_id=cat.id, slug="air-max")
        svc = _make_supplier_service()

        handler = CreateProductHandler(
            product_repo=uow.products,
            brand_repo=uow.brands,
            category_repo=uow.categories,
            supplier_query_service=svc,
            media_repo=uow.media_assets,
            uow=uow,
            logger=_make_logger(),
        )

        with pytest.raises(ProductSlugConflictError):
            await handler.handle(
                CreateProductCommand(
                    title_i18n={"en": "Air Max 2", "ru": "Эйр Макс 2"},
                    slug="air-max",
                    brand_id=brand.id,
                    primary_category_id=cat.id,
                )
            )

        assert uow.committed is False

    async def test_supplier_inactive(self):
        uow = FakeUnitOfWork()
        brand = _seed_brand(uow)
        cat = _seed_category(uow)
        supplier_id = uuid.uuid4()
        svc = _make_supplier_service(
            raises=SupplierInactiveError(supplier_id=supplier_id),
        )

        handler = CreateProductHandler(
            product_repo=uow.products,
            brand_repo=uow.brands,
            category_repo=uow.categories,
            supplier_query_service=svc,
            media_repo=uow.media_assets,
            uow=uow,
            logger=_make_logger(),
        )

        with pytest.raises(SupplierInactiveError):
            await handler.handle(
                CreateProductCommand(
                    title_i18n={"en": "Air Max", "ru": "Эйр Макс"},
                    slug="air-max",
                    brand_id=brand.id,
                    primary_category_id=cat.id,
                    supplier_id=supplier_id,
                )
            )

        assert uow.committed is False

    async def test_cross_border_no_source_url(self):
        uow = FakeUnitOfWork()
        brand = _seed_brand(uow)
        cat = _seed_category(uow)
        supplier_id = uuid.uuid4()
        info = SupplierInfo(
            id=supplier_id,
            name="Poizon",
            type=SupplierType.CROSS_BORDER,
            is_active=True,
        )
        svc = _make_supplier_service(supplier_info=info)

        handler = CreateProductHandler(
            product_repo=uow.products,
            brand_repo=uow.brands,
            category_repo=uow.categories,
            supplier_query_service=svc,
            media_repo=uow.media_assets,
            uow=uow,
            logger=_make_logger(),
        )

        with pytest.raises(SourceUrlRequiredError):
            await handler.handle(
                CreateProductCommand(
                    title_i18n={"en": "Air Max", "ru": "Эйр Макс"},
                    slug="air-max",
                    brand_id=brand.id,
                    primary_category_id=cat.id,
                    supplier_id=supplier_id,
                    source_url=None,
                )
            )

        assert uow.committed is False


# ============================================================================
# TestUpdateProduct
# ============================================================================


class TestUpdateProduct:
    """Tests for UpdateProductHandler."""

    async def test_happy_path_update_title(self):
        uow = FakeUnitOfWork()
        brand = _seed_brand(uow)
        cat = _seed_category(uow)
        product = _seed_product(uow, brand_id=brand.id, category_id=cat.id)
        image_backend = _make_image_backend()

        handler = UpdateProductHandler(
            product_repo=uow.products,
            brand_repo=uow.brands,
            category_repo=uow.categories,
            media_repo=uow.media_assets,
            image_backend=image_backend,
            uow=uow,
            logger=_make_logger(),
        )

        result = await handler.handle(
            UpdateProductCommand(
                product_id=product.id,
                title_i18n={"en": "Updated Title", "ru": "Обновленный"},
                _provided_fields=frozenset({"title_i18n"}),
            )
        )

        assert isinstance(result, UpdateProductResult)
        assert result.id == product.id
        assert uow.committed is True
        updated = uow.products._store[product.id]
        assert updated.title_i18n["en"] == "Updated Title"

    async def test_happy_path_update_slug_no_conflict(self):
        uow = FakeUnitOfWork()
        brand = _seed_brand(uow)
        cat = _seed_category(uow)
        product = _seed_product(uow, brand_id=brand.id, category_id=cat.id)
        image_backend = _make_image_backend()

        handler = UpdateProductHandler(
            product_repo=uow.products,
            brand_repo=uow.brands,
            category_repo=uow.categories,
            media_repo=uow.media_assets,
            image_backend=image_backend,
            uow=uow,
            logger=_make_logger(),
        )

        result = await handler.handle(
            UpdateProductCommand(
                product_id=product.id,
                slug="new-slug",
                _provided_fields=frozenset({"slug"}),
            )
        )

        assert uow.committed is True
        assert uow.products._store[product.id].slug == "new-slug"

    async def test_product_not_found(self):
        uow = FakeUnitOfWork()
        image_backend = _make_image_backend()

        handler = UpdateProductHandler(
            product_repo=uow.products,
            brand_repo=uow.brands,
            category_repo=uow.categories,
            media_repo=uow.media_assets,
            image_backend=image_backend,
            uow=uow,
            logger=_make_logger(),
        )

        with pytest.raises(ProductNotFoundError):
            await handler.handle(
                UpdateProductCommand(
                    product_id=uuid.uuid4(),
                    title_i18n={"en": "X", "ru": "Y"},
                    _provided_fields=frozenset({"title_i18n"}),
                )
            )

        assert uow.committed is False

    async def test_version_mismatch(self):
        uow = FakeUnitOfWork()
        brand = _seed_brand(uow)
        cat = _seed_category(uow)
        product = _seed_product(uow, brand_id=brand.id, category_id=cat.id)
        image_backend = _make_image_backend()

        handler = UpdateProductHandler(
            product_repo=uow.products,
            brand_repo=uow.brands,
            category_repo=uow.categories,
            media_repo=uow.media_assets,
            image_backend=image_backend,
            uow=uow,
            logger=_make_logger(),
        )

        with pytest.raises(ConcurrencyError):
            await handler.handle(
                UpdateProductCommand(
                    product_id=product.id,
                    title_i18n={"en": "X", "ru": "Y"},
                    version=999,
                    _provided_fields=frozenset({"title_i18n"}),
                )
            )

        assert uow.committed is False

    async def test_slug_conflict(self):
        uow = FakeUnitOfWork()
        brand = _seed_brand(uow)
        cat = _seed_category(uow)
        product = _seed_product(uow, brand_id=brand.id, category_id=cat.id)
        _seed_product(uow, brand_id=brand.id, category_id=cat.id, slug="taken-slug")
        image_backend = _make_image_backend()

        handler = UpdateProductHandler(
            product_repo=uow.products,
            brand_repo=uow.brands,
            category_repo=uow.categories,
            media_repo=uow.media_assets,
            image_backend=image_backend,
            uow=uow,
            logger=_make_logger(),
        )

        with pytest.raises(ProductSlugConflictError):
            await handler.handle(
                UpdateProductCommand(
                    product_id=product.id,
                    slug="taken-slug",
                    _provided_fields=frozenset({"slug"}),
                )
            )

        assert uow.committed is False

    async def test_brand_not_found_when_updating_brand(self):
        uow = FakeUnitOfWork()
        brand = _seed_brand(uow)
        cat = _seed_category(uow)
        product = _seed_product(uow, brand_id=brand.id, category_id=cat.id)
        image_backend = _make_image_backend()

        handler = UpdateProductHandler(
            product_repo=uow.products,
            brand_repo=uow.brands,
            category_repo=uow.categories,
            media_repo=uow.media_assets,
            image_backend=image_backend,
            uow=uow,
            logger=_make_logger(),
        )

        with pytest.raises(BrandNotFoundError):
            await handler.handle(
                UpdateProductCommand(
                    product_id=product.id,
                    brand_id=uuid.uuid4(),
                    _provided_fields=frozenset({"brand_id"}),
                )
            )

        assert uow.committed is False

    async def test_brand_id_none_in_provided_fields(self):
        uow = FakeUnitOfWork()
        brand = _seed_brand(uow)
        cat = _seed_category(uow)
        product = _seed_product(uow, brand_id=brand.id, category_id=cat.id)
        image_backend = _make_image_backend()

        handler = UpdateProductHandler(
            product_repo=uow.products,
            brand_repo=uow.brands,
            category_repo=uow.categories,
            media_repo=uow.media_assets,
            image_backend=image_backend,
            uow=uow,
            logger=_make_logger(),
        )

        with pytest.raises(UnprocessableEntityError):
            await handler.handle(
                UpdateProductCommand(
                    product_id=product.id,
                    brand_id=None,
                    _provided_fields=frozenset({"brand_id"}),
                )
            )

        assert uow.committed is False


# ============================================================================
# TestDeleteProduct
# ============================================================================


class TestDeleteProduct:
    """Tests for DeleteProductHandler."""

    async def test_happy_path(self):
        uow = FakeUnitOfWork()
        brand = _seed_brand(uow)
        cat = _seed_category(uow)
        product = _seed_product(uow, brand_id=brand.id, category_id=cat.id)

        handler = DeleteProductHandler(
            product_repo=uow.products,
            uow=uow,
            logger=_make_logger(),
        )

        await handler.handle(DeleteProductCommand(product_id=product.id))

        assert uow.committed is True
        deleted = uow.products._store[product.id]
        assert deleted.deleted_at is not None

    async def test_product_not_found(self):
        uow = FakeUnitOfWork()

        handler = DeleteProductHandler(
            product_repo=uow.products,
            uow=uow,
            logger=_make_logger(),
        )

        with pytest.raises(ProductNotFoundError):
            await handler.handle(DeleteProductCommand(product_id=uuid.uuid4()))

        assert uow.committed is False


# ============================================================================
# TestChangeProductStatus
# ============================================================================


class TestChangeProductStatus:
    """Tests for ChangeProductStatusHandler."""

    async def test_happy_path_draft_to_enriching(self):
        """Transition DRAFT -> ENRICHING (simplest valid transition, no media or SKU needed)."""
        uow = FakeUnitOfWork()
        brand = _seed_brand(uow)
        cat = _seed_category(uow)
        product = _seed_product(uow, brand_id=brand.id, category_id=cat.id)

        handler = ChangeProductStatusHandler(
            product_repo=uow.products,
            media_repo=uow.media_assets,
            uow=uow,
            logger=_make_logger(),
        )

        await handler.handle(
            ChangeProductStatusCommand(
                product_id=product.id,
                new_status=ProductStatus.ENRICHING,
            )
        )

        assert uow.committed is True
        assert uow.products._store[product.id].status == ProductStatus.ENRICHING

    async def test_product_not_found(self):
        uow = FakeUnitOfWork()

        handler = ChangeProductStatusHandler(
            product_repo=uow.products,
            media_repo=uow.media_assets,
            uow=uow,
            logger=_make_logger(),
        )

        with pytest.raises(ProductNotFoundError):
            await handler.handle(
                ChangeProductStatusCommand(
                    product_id=uuid.uuid4(),
                    new_status=ProductStatus.ENRICHING,
                )
            )

        assert uow.committed is False

    async def test_publish_without_media(self):
        """Publishing requires media assets (handler check)."""
        uow = FakeUnitOfWork()
        brand = _seed_brand(uow)
        cat = _seed_category(uow)
        product = _seed_product(uow, brand_id=brand.id, category_id=cat.id)
        # No media seeded -- handler should raise ProductNotReadyError

        handler = ChangeProductStatusHandler(
            product_repo=uow.products,
            media_repo=uow.media_assets,
            uow=uow,
            logger=_make_logger(),
        )

        with pytest.raises(ProductNotReadyError):
            await handler.handle(
                ChangeProductStatusCommand(
                    product_id=product.id,
                    new_status=ProductStatus.PUBLISHED,
                )
            )

        assert uow.committed is False

    async def test_invalid_transition(self):
        """DRAFT -> ARCHIVED is not a valid FSM transition."""
        uow = FakeUnitOfWork()
        brand = _seed_brand(uow)
        cat = _seed_category(uow)
        product = _seed_product(uow, brand_id=brand.id, category_id=cat.id)
        # Product is DRAFT; DRAFT -> ARCHIVED is invalid

        handler = ChangeProductStatusHandler(
            product_repo=uow.products,
            media_repo=uow.media_assets,
            uow=uow,
            logger=_make_logger(),
        )

        with pytest.raises(InvalidStatusTransitionError):
            await handler.handle(
                ChangeProductStatusCommand(
                    product_id=product.id,
                    new_status=ProductStatus.ARCHIVED,
                )
            )

        assert uow.committed is False


# ============================================================================
# TestAssignProductAttribute
# ============================================================================


class TestAssignProductAttribute:
    """Tests for AssignProductAttributeHandler."""

    def _make_handler(self, uow):
        return AssignProductAttributeHandler(
            product_repo=uow.products,
            pav_repo=uow.product_attribute_values,
            attribute_repo=uow.attributes,
            attribute_value_repo=uow.attribute_values,
            category_repo=uow.categories,
            template_repo=uow.attribute_templates,
            template_binding_repo=uow.template_bindings,
            uow=uow,
            logger=_make_logger(),
        )

    async def test_happy_path(self):
        uow = FakeUnitOfWork()
        tmpl = _seed_template(uow)
        cat = _seed_category(uow, template_id=tmpl.id)
        brand = _seed_brand(uow)
        product = _seed_product(uow, brand_id=brand.id, category_id=cat.id)
        group = _seed_attribute_group(uow)
        attr = _seed_attribute(uow, group_id=group.id)
        val = _seed_attribute_value(uow, attribute_id=attr.id)
        _seed_binding(uow, template_id=tmpl.id, attribute_id=attr.id)

        handler = self._make_handler(uow)
        result = await handler.handle(
            AssignProductAttributeCommand(
                product_id=product.id,
                attribute_id=attr.id,
                attribute_value_id=val.id,
            )
        )

        assert isinstance(result, AssignProductAttributeResult)
        assert result.pav_id is not None
        assert uow.committed is True
        assert result.pav_id in uow.product_attribute_values._store

    async def test_product_not_found(self):
        uow = FakeUnitOfWork()
        handler = self._make_handler(uow)

        with pytest.raises(ProductNotFoundError):
            await handler.handle(
                AssignProductAttributeCommand(
                    product_id=uuid.uuid4(),
                    attribute_id=uuid.uuid4(),
                    attribute_value_id=uuid.uuid4(),
                )
            )

        assert uow.committed is False

    async def test_attribute_not_in_template(self):
        uow = FakeUnitOfWork()
        tmpl = _seed_template(uow)
        cat = _seed_category(uow, template_id=tmpl.id)
        brand = _seed_brand(uow)
        product = _seed_product(uow, brand_id=brand.id, category_id=cat.id)
        # Attribute NOT bound to template
        group = _seed_attribute_group(uow)
        attr = _seed_attribute(uow, group_id=group.id)

        handler = self._make_handler(uow)

        with pytest.raises(AttributeNotInTemplateError):
            await handler.handle(
                AssignProductAttributeCommand(
                    product_id=product.id,
                    attribute_id=attr.id,
                    attribute_value_id=uuid.uuid4(),
                )
            )

        assert uow.committed is False

    async def test_attribute_not_found(self):
        uow = FakeUnitOfWork()
        cat = _seed_category(uow)  # No template
        brand = _seed_brand(uow)
        product = _seed_product(uow, brand_id=brand.id, category_id=cat.id)

        handler = self._make_handler(uow)

        with pytest.raises(AttributeNotFoundError):
            await handler.handle(
                AssignProductAttributeCommand(
                    product_id=product.id,
                    attribute_id=uuid.uuid4(),
                    attribute_value_id=uuid.uuid4(),
                )
            )

        assert uow.committed is False

    async def test_attribute_wrong_level(self):
        uow = FakeUnitOfWork()
        cat = _seed_category(uow)
        brand = _seed_brand(uow)
        product = _seed_product(uow, brand_id=brand.id, category_id=cat.id)
        group = _seed_attribute_group(uow)
        attr = _seed_attribute(
            uow, group_id=group.id, level=AttributeLevel.VARIANT
        )

        handler = self._make_handler(uow)

        with pytest.raises(AttributeLevelMismatchError):
            await handler.handle(
                AssignProductAttributeCommand(
                    product_id=product.id,
                    attribute_id=attr.id,
                    attribute_value_id=uuid.uuid4(),
                )
            )

        assert uow.committed is False

    async def test_attribute_not_dictionary(self):
        uow = FakeUnitOfWork()
        cat = _seed_category(uow)
        brand = _seed_brand(uow)
        product = _seed_product(uow, brand_id=brand.id, category_id=cat.id)
        group = _seed_attribute_group(uow)
        attr = _seed_attribute(uow, group_id=group.id, is_dictionary=False)

        handler = self._make_handler(uow)

        with pytest.raises(AttributeNotDictionaryError):
            await handler.handle(
                AssignProductAttributeCommand(
                    product_id=product.id,
                    attribute_id=attr.id,
                    attribute_value_id=uuid.uuid4(),
                )
            )

        assert uow.committed is False

    async def test_value_not_found(self):
        uow = FakeUnitOfWork()
        cat = _seed_category(uow)
        brand = _seed_brand(uow)
        product = _seed_product(uow, brand_id=brand.id, category_id=cat.id)
        group = _seed_attribute_group(uow)
        attr = _seed_attribute(uow, group_id=group.id)

        handler = self._make_handler(uow)

        with pytest.raises(AttributeValueNotFoundError):
            await handler.handle(
                AssignProductAttributeCommand(
                    product_id=product.id,
                    attribute_id=attr.id,
                    attribute_value_id=uuid.uuid4(),
                )
            )

        assert uow.committed is False

    async def test_value_wrong_attribute(self):
        uow = FakeUnitOfWork()
        cat = _seed_category(uow)
        brand = _seed_brand(uow)
        product = _seed_product(uow, brand_id=brand.id, category_id=cat.id)
        group = _seed_attribute_group(uow)
        attr = _seed_attribute(uow, group_id=group.id)
        # Value belongs to a different attribute
        other_attr_id = uuid.uuid4()
        val = AttributeValue.create(
            attribute_id=other_attr_id,
            code="blue",
            slug="blue",
            value_i18n={"en": "Blue", "ru": "Синий"},
        )
        uow.attribute_values._store[val.id] = val

        handler = self._make_handler(uow)

        with pytest.raises(AttributeValueNotFoundError):
            await handler.handle(
                AssignProductAttributeCommand(
                    product_id=product.id,
                    attribute_id=attr.id,
                    attribute_value_id=val.id,
                )
            )

        assert uow.committed is False

    async def test_duplicate_assignment(self):
        uow = FakeUnitOfWork()
        cat = _seed_category(uow)
        brand = _seed_brand(uow)
        product = _seed_product(uow, brand_id=brand.id, category_id=cat.id)
        group = _seed_attribute_group(uow)
        attr = _seed_attribute(uow, group_id=group.id)
        val = _seed_attribute_value(uow, attribute_id=attr.id)
        # Pre-seed an existing assignment
        existing_pav = ProductAttributeValue.create(
            product_id=product.id,
            attribute_id=attr.id,
            attribute_value_id=val.id,
        )
        uow.product_attribute_values._store[existing_pav.id] = existing_pav

        handler = self._make_handler(uow)

        with pytest.raises(DuplicateProductAttributeError):
            await handler.handle(
                AssignProductAttributeCommand(
                    product_id=product.id,
                    attribute_id=attr.id,
                    attribute_value_id=val.id,
                )
            )

        assert uow.committed is False

    async def test_category_no_template(self):
        """When category has no template, template check is skipped."""
        uow = FakeUnitOfWork()
        cat = _seed_category(uow)  # No template_id
        brand = _seed_brand(uow)
        product = _seed_product(uow, brand_id=brand.id, category_id=cat.id)
        group = _seed_attribute_group(uow)
        attr = _seed_attribute(uow, group_id=group.id)
        val = _seed_attribute_value(uow, attribute_id=attr.id)

        handler = self._make_handler(uow)
        result = await handler.handle(
            AssignProductAttributeCommand(
                product_id=product.id,
                attribute_id=attr.id,
                attribute_value_id=val.id,
            )
        )

        assert uow.committed is True
        assert result.pav_id in uow.product_attribute_values._store


# ============================================================================
# TestBulkAssignProductAttributes
# ============================================================================


class TestBulkAssignProductAttributes:
    """Tests for BulkAssignProductAttributesHandler."""

    def _make_handler(self, uow):
        return BulkAssignProductAttributesHandler(
            product_repo=uow.products,
            pav_repo=uow.product_attribute_values,
            attribute_repo=uow.attributes,
            attribute_value_repo=uow.attribute_values,
            category_repo=uow.categories,
            template_repo=uow.attribute_templates,
            template_binding_repo=uow.template_bindings,
            uow=uow,
            logger=_make_logger(),
        )

    async def test_happy_path_multiple_items(self):
        uow = FakeUnitOfWork()
        cat = _seed_category(uow)
        brand = _seed_brand(uow)
        product = _seed_product(uow, brand_id=brand.id, category_id=cat.id)
        group = _seed_attribute_group(uow)

        # Create two distinct attributes with values
        attr1 = Attribute.create(
            code="color",
            slug="color",
            name_i18n={"en": "Color", "ru": "Цвет"},
            data_type=AttributeDataType.STRING,
            ui_type=AttributeUIType.DROPDOWN,
            is_dictionary=True,
            group_id=group.id,
            level=AttributeLevel.PRODUCT,
        )
        uow.attributes._store[attr1.id] = attr1
        val1 = AttributeValue.create(
            attribute_id=attr1.id,
            code="red",
            slug="red",
            value_i18n={"en": "Red", "ru": "Красный"},
        )
        uow.attribute_values._store[val1.id] = val1

        attr2 = Attribute.create(
            code="material",
            slug="material",
            name_i18n={"en": "Material", "ru": "Материал"},
            data_type=AttributeDataType.STRING,
            ui_type=AttributeUIType.DROPDOWN,
            is_dictionary=True,
            group_id=group.id,
            level=AttributeLevel.PRODUCT,
        )
        uow.attributes._store[attr2.id] = attr2
        val2 = AttributeValue.create(
            attribute_id=attr2.id,
            code="leather",
            slug="leather",
            value_i18n={"en": "Leather", "ru": "Кожа"},
        )
        uow.attribute_values._store[val2.id] = val2

        handler = self._make_handler(uow)
        result = await handler.handle(
            BulkAssignProductAttributesCommand(
                product_id=product.id,
                items=[
                    AttributeAssignmentItem(
                        attribute_id=attr1.id, attribute_value_id=val1.id
                    ),
                    AttributeAssignmentItem(
                        attribute_id=attr2.id, attribute_value_id=val2.id
                    ),
                ],
            )
        )

        assert isinstance(result, BulkAssignProductAttributesResult)
        assert result.assigned_count == 2
        assert len(result.pav_ids) == 2
        assert uow.committed is True

    async def test_too_many_items(self):
        uow = FakeUnitOfWork()
        cat = _seed_category(uow)
        brand = _seed_brand(uow)
        _seed_product(uow, brand_id=brand.id, category_id=cat.id)
        handler = self._make_handler(uow)

        items = [
            AttributeAssignmentItem(
                attribute_id=uuid.uuid4(), attribute_value_id=uuid.uuid4()
            )
            for _ in range(101)
        ]

        with pytest.raises(ValueError, match="more than 100"):
            await handler.handle(
                BulkAssignProductAttributesCommand(
                    product_id=uuid.uuid4(),
                    items=items,
                )
            )

        assert uow.committed is False

    async def test_duplicate_within_batch(self):
        uow = FakeUnitOfWork()
        cat = _seed_category(uow)
        brand = _seed_brand(uow)
        product = _seed_product(uow, brand_id=brand.id, category_id=cat.id)
        handler = self._make_handler(uow)

        attr_id = uuid.uuid4()

        with pytest.raises(DuplicateProductAttributeError):
            await handler.handle(
                BulkAssignProductAttributesCommand(
                    product_id=product.id,
                    items=[
                        AttributeAssignmentItem(
                            attribute_id=attr_id, attribute_value_id=uuid.uuid4()
                        ),
                        AttributeAssignmentItem(
                            attribute_id=attr_id, attribute_value_id=uuid.uuid4()
                        ),
                    ],
                )
            )

        assert uow.committed is False

    async def test_item_validation_failure_rejects_batch(self):
        """If one item has an invalid attribute, the entire batch is rejected."""
        uow = FakeUnitOfWork()
        cat = _seed_category(uow)
        brand = _seed_brand(uow)
        product = _seed_product(uow, brand_id=brand.id, category_id=cat.id)
        group = _seed_attribute_group(uow)

        # First attribute: valid
        attr1 = Attribute.create(
            code="color",
            slug="color",
            name_i18n={"en": "Color", "ru": "Цвет"},
            data_type=AttributeDataType.STRING,
            ui_type=AttributeUIType.DROPDOWN,
            is_dictionary=True,
            group_id=group.id,
            level=AttributeLevel.PRODUCT,
        )
        uow.attributes._store[attr1.id] = attr1
        val1 = AttributeValue.create(
            attribute_id=attr1.id,
            code="red",
            slug="red",
            value_i18n={"en": "Red", "ru": "Красный"},
        )
        uow.attribute_values._store[val1.id] = val1

        # Second attribute: does NOT exist in repo -> AttributeNotFoundError
        nonexistent_attr_id = uuid.uuid4()

        handler = self._make_handler(uow)

        with pytest.raises(AttributeNotFoundError):
            await handler.handle(
                BulkAssignProductAttributesCommand(
                    product_id=product.id,
                    items=[
                        AttributeAssignmentItem(
                            attribute_id=attr1.id, attribute_value_id=val1.id
                        ),
                        AttributeAssignmentItem(
                            attribute_id=nonexistent_attr_id,
                            attribute_value_id=uuid.uuid4(),
                        ),
                    ],
                )
            )

        assert uow.committed is False


# ============================================================================
# TestDeleteProductAttribute
# ============================================================================


class TestDeleteProductAttribute:
    """Tests for DeleteProductAttributeHandler."""

    async def test_happy_path(self):
        uow = FakeUnitOfWork()
        product_id = uuid.uuid4()
        attr_id = uuid.uuid4()
        pav = ProductAttributeValue.create(
            product_id=product_id,
            attribute_id=attr_id,
            attribute_value_id=uuid.uuid4(),
        )
        uow.product_attribute_values._store[pav.id] = pav

        handler = DeleteProductAttributeHandler(
            pav_repo=uow.product_attribute_values,
            uow=uow,
            logger=_make_logger(),
        )

        await handler.handle(
            DeleteProductAttributeCommand(
                product_id=product_id,
                attribute_id=attr_id,
            )
        )

        assert uow.committed is True
        assert pav.id not in uow.product_attribute_values._store

    async def test_assignment_not_found(self):
        uow = FakeUnitOfWork()

        handler = DeleteProductAttributeHandler(
            pav_repo=uow.product_attribute_values,
            uow=uow,
            logger=_make_logger(),
        )

        with pytest.raises(ProductAttributeValueNotFoundError):
            await handler.handle(
                DeleteProductAttributeCommand(
                    product_id=uuid.uuid4(),
                    attribute_id=uuid.uuid4(),
                )
            )

        assert uow.committed is False
