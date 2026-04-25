"""Unit tests for all SKU command handlers (CMD-06).

Tests handler orchestration: product repository interactions, SKU code uniqueness,
variant hash uniqueness, cartesian product matrix generation, pricing via Money,
UoW commit/rollback, and domain event emission through the aggregate.
Uses FakeUnitOfWork for real in-memory repository behavior.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.modules.catalog.application.commands.add_sku import (
    AddSKUCommand,
    AddSKUHandler,
    AddSKUResult,
)
from src.modules.catalog.application.commands.delete_sku import (
    DeleteSKUCommand,
    DeleteSKUHandler,
)
from src.modules.catalog.application.commands.generate_sku_matrix import (
    AttributeSelection,
    GenerateSKUMatrixCommand,
    GenerateSKUMatrixHandler,
    GenerateSKUMatrixResult,
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
    TemplateAttributeBinding,
)
from src.modules.catalog.domain.events import SKUAddedEvent, SKUDeletedEvent
from src.modules.catalog.domain.exceptions import (
    AttributeLevelMismatchError,
    AttributeNotFoundError,
    AttributeValueNotFoundError,
    ConcurrencyError,
    DuplicateVariantCombinationError,
    ProductNotFoundError,
    SKUCodeConflictError,
    SKUNotFoundError,
)
from src.modules.catalog.domain.value_objects import (
    AttributeDataType,
    AttributeLevel,
    AttributeUIType,
    Money,
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
    # Clear ProductCreatedEvent emitted by create()
    product.clear_domain_events()
    uow.products._store[product.id] = product
    return product


def _seed_product_with_template(uow):
    """Create product with a category that has a template, plus all supporting entities.

    Returns (product, template, variant-level attribute, [value1, value2]).
    """
    template = AttributeTemplate.create(
        code="shoe-tmpl",
        name_i18n={"en": "Shoe Template", "ru": "Шаблон обуви"},
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
    uow.attribute_values._store[val1.id] = val1
    uow.attribute_values._store[val2.id] = val2

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

    return product, template, attr, [val1, val2]


# ============================================================================
# TestAddSKU
# ============================================================================


class TestAddSKU:
    """Tests for AddSKUHandler."""

    async def test_happy_path_creates_sku(self):
        uow = FakeUnitOfWork()
        product = _seed_product(uow)
        variant_id = product.variants[0].id

        handler = AddSKUHandler(
            cache=AsyncMock(), product_repo=uow.products, uow=uow, logger=_make_logger()
        )
        result = await handler.handle(
            AddSKUCommand(
                product_id=product.id,
                variant_id=variant_id,
                sku_code="SKU-001",
            )
        )

        assert isinstance(result, AddSKUResult)
        assert result.sku_id is not None
        # SKU exists on the product's variant
        sku = product.find_sku(result.sku_id)
        assert sku is not None
        assert sku.sku_code == "SKU-001"
        assert uow.committed is True

    async def test_creates_sku_with_price(self):
        uow = FakeUnitOfWork()
        product = _seed_product(uow)
        variant_id = product.variants[0].id

        handler = AddSKUHandler(
            cache=AsyncMock(), product_repo=uow.products, uow=uow, logger=_make_logger()
        )
        result = await handler.handle(
            AddSKUCommand(
                product_id=product.id,
                variant_id=variant_id,
                sku_code="SKU-002",
                price_amount=1000,
                price_currency="RUB",
            )
        )

        sku = product.find_sku(result.sku_id)
        assert sku is not None
        assert sku.price == Money(amount=1000, currency="RUB")

    async def test_product_not_found(self):
        uow = FakeUnitOfWork()

        handler = AddSKUHandler(
            cache=AsyncMock(), product_repo=uow.products, uow=uow, logger=_make_logger()
        )
        with pytest.raises(ProductNotFoundError):
            await handler.handle(
                AddSKUCommand(
                    product_id=uuid.uuid4(),
                    variant_id=uuid.uuid4(),
                    sku_code="SKU-003",
                )
            )
        assert uow.committed is False

    async def test_sku_code_conflict(self):
        uow = FakeUnitOfWork()
        # Create first product with SKU code "TAKEN"
        p1 = _seed_product(uow, slug="product-1")
        p1.add_sku(
            variant_id=p1.variants[0].id,
            sku_code="TAKEN",
            price=Money(amount=100, currency="RUB"),
        )
        p1.clear_domain_events()
        uow.products._store[p1.id] = p1

        # Try to add another SKU with same code on another product
        p2 = _seed_product(uow, slug="product-2")

        handler = AddSKUHandler(
            cache=AsyncMock(), product_repo=uow.products, uow=uow, logger=_make_logger()
        )
        with pytest.raises(SKUCodeConflictError):
            await handler.handle(
                AddSKUCommand(
                    product_id=p2.id,
                    variant_id=p2.variants[0].id,
                    sku_code="TAKEN",
                )
            )
        assert uow.committed is False

    async def test_duplicate_variant_combination(self):
        uow = FakeUnitOfWork()
        product = _seed_product(uow)
        variant_id = product.variants[0].id
        attr_id = uuid.uuid4()
        val_id = uuid.uuid4()

        # Add first SKU with variant_attributes
        product.add_sku(
            variant_id=variant_id,
            sku_code="SKU-FIRST",
            variant_attributes=[(attr_id, val_id)],
        )
        product.clear_domain_events()
        uow.products._store[product.id] = product

        handler = AddSKUHandler(
            cache=AsyncMock(), product_repo=uow.products, uow=uow, logger=_make_logger()
        )
        with pytest.raises(DuplicateVariantCombinationError):
            await handler.handle(
                AddSKUCommand(
                    product_id=product.id,
                    variant_id=variant_id,
                    sku_code="SKU-SECOND",
                    variant_attributes=[(attr_id, val_id)],
                )
            )
        assert uow.committed is False

    async def test_emits_sku_added_event(self):
        uow = FakeUnitOfWork()
        product = _seed_product(uow)
        variant_id = product.variants[0].id

        handler = AddSKUHandler(
            cache=AsyncMock(), product_repo=uow.products, uow=uow, logger=_make_logger()
        )
        result = await handler.handle(
            AddSKUCommand(
                product_id=product.id,
                variant_id=variant_id,
                sku_code="SKU-EVENT",
            )
        )

        sku_added_events = [
            e for e in uow.collected_events if isinstance(e, SKUAddedEvent)
        ]
        assert len(sku_added_events) == 1
        assert sku_added_events[0].sku_id == result.sku_id
        assert sku_added_events[0].product_id == product.id
        assert sku_added_events[0].variant_id == variant_id


# ============================================================================
# TestUpdateSKU
# ============================================================================


class TestUpdateSKU:
    """Tests for UpdateSKUHandler."""

    async def test_happy_path_updates_sku_code(self):
        uow = FakeUnitOfWork()
        product = _seed_product(uow)
        variant_id = product.variants[0].id

        sku = product.add_sku(
            variant_id=variant_id,
            sku_code="OLD-CODE",
        )
        product.clear_domain_events()
        uow.products._store[product.id] = product

        handler = UpdateSKUHandler(
            cache=AsyncMock(), product_repo=uow.products, uow=uow, logger=_make_logger()
        )
        result = await handler.handle(
            UpdateSKUCommand(
                product_id=product.id,
                sku_id=sku.id,
                sku_code="NEW-CODE",
            )
        )

        assert result.id == sku.id
        assert sku.sku_code == "NEW-CODE"
        assert uow.committed is True

    async def test_happy_path_updates_price(self):
        uow = FakeUnitOfWork()
        product = _seed_product(uow)
        variant_id = product.variants[0].id

        sku = product.add_sku(
            variant_id=variant_id,
            sku_code="PRICE-SKU",
            price=Money(amount=1000, currency="RUB"),
        )
        product.clear_domain_events()
        uow.products._store[product.id] = product

        handler = UpdateSKUHandler(
            cache=AsyncMock(), product_repo=uow.products, uow=uow, logger=_make_logger()
        )
        await handler.handle(
            UpdateSKUCommand(
                product_id=product.id,
                sku_id=sku.id,
                price_amount=2000,
            )
        )

        assert sku.price.amount == 2000
        assert uow.committed is True

    async def test_product_not_found(self):
        uow = FakeUnitOfWork()

        handler = UpdateSKUHandler(
            cache=AsyncMock(), product_repo=uow.products, uow=uow, logger=_make_logger()
        )
        with pytest.raises(ProductNotFoundError):
            await handler.handle(
                UpdateSKUCommand(
                    product_id=uuid.uuid4(),
                    sku_id=uuid.uuid4(),
                )
            )
        assert uow.committed is False

    async def test_sku_not_found(self):
        uow = FakeUnitOfWork()
        product = _seed_product(uow)

        handler = UpdateSKUHandler(
            cache=AsyncMock(), product_repo=uow.products, uow=uow, logger=_make_logger()
        )
        with pytest.raises(SKUNotFoundError):
            await handler.handle(
                UpdateSKUCommand(
                    product_id=product.id,
                    sku_id=uuid.uuid4(),
                )
            )
        assert uow.committed is False

    async def test_version_mismatch(self):
        uow = FakeUnitOfWork()
        product = _seed_product(uow)
        variant_id = product.variants[0].id

        sku = product.add_sku(
            variant_id=variant_id,
            sku_code="VERSION-SKU",
        )
        product.clear_domain_events()
        uow.products._store[product.id] = product

        handler = UpdateSKUHandler(
            cache=AsyncMock(), product_repo=uow.products, uow=uow, logger=_make_logger()
        )
        with pytest.raises(ConcurrencyError):
            await handler.handle(
                UpdateSKUCommand(
                    product_id=product.id,
                    sku_id=sku.id,
                    sku_code="CONFLICT",
                    version=999,
                )
            )
        assert uow.committed is False

    async def test_sku_code_conflict_on_update(self):
        uow = FakeUnitOfWork()
        # Product 1 has SKU with code "TAKEN"
        p1 = _seed_product(uow, slug="update-p1")
        p1.add_sku(
            variant_id=p1.variants[0].id,
            sku_code="TAKEN",
        )
        p1.clear_domain_events()
        uow.products._store[p1.id] = p1

        # Product 2 has SKU with code "MY-CODE"
        p2 = _seed_product(uow, slug="update-p2")
        sku2 = p2.add_sku(
            variant_id=p2.variants[0].id,
            sku_code="MY-CODE",
        )
        p2.clear_domain_events()
        uow.products._store[p2.id] = p2

        handler = UpdateSKUHandler(
            cache=AsyncMock(), product_repo=uow.products, uow=uow, logger=_make_logger()
        )
        with pytest.raises(SKUCodeConflictError):
            await handler.handle(
                UpdateSKUCommand(
                    product_id=p2.id,
                    sku_id=sku2.id,
                    sku_code="TAKEN",
                )
            )
        assert uow.committed is False


# ============================================================================
# TestDeleteSKU
# ============================================================================


class TestDeleteSKU:
    """Tests for DeleteSKUHandler."""

    async def test_happy_path_soft_deletes(self):
        uow = FakeUnitOfWork()
        product = _seed_product(uow)
        variant_id = product.variants[0].id

        sku = product.add_sku(
            variant_id=variant_id,
            sku_code="DEL-SKU",
        )
        product.clear_domain_events()
        uow.products._store[product.id] = product

        handler = DeleteSKUHandler(
            cache=AsyncMock(), product_repo=uow.products, uow=uow, logger=_make_logger()
        )
        await handler.handle(
            DeleteSKUCommand(
                product_id=product.id,
                sku_id=sku.id,
            )
        )

        assert sku.deleted_at is not None
        assert uow.committed is True

    async def test_product_not_found(self):
        uow = FakeUnitOfWork()

        handler = DeleteSKUHandler(
            cache=AsyncMock(), product_repo=uow.products, uow=uow, logger=_make_logger()
        )
        with pytest.raises(ProductNotFoundError):
            await handler.handle(
                DeleteSKUCommand(
                    product_id=uuid.uuid4(),
                    sku_id=uuid.uuid4(),
                )
            )
        assert uow.committed is False

    async def test_sku_not_found(self):
        uow = FakeUnitOfWork()
        product = _seed_product(uow)

        handler = DeleteSKUHandler(
            cache=AsyncMock(), product_repo=uow.products, uow=uow, logger=_make_logger()
        )
        with pytest.raises(SKUNotFoundError):
            await handler.handle(
                DeleteSKUCommand(
                    product_id=product.id,
                    sku_id=uuid.uuid4(),
                )
            )
        assert uow.committed is False

    async def test_emits_sku_deleted_event(self):
        uow = FakeUnitOfWork()
        product = _seed_product(uow)
        variant_id = product.variants[0].id

        sku = product.add_sku(
            variant_id=variant_id,
            sku_code="DEL-EVENT-SKU",
        )
        product.clear_domain_events()
        uow.products._store[product.id] = product

        handler = DeleteSKUHandler(
            cache=AsyncMock(), product_repo=uow.products, uow=uow, logger=_make_logger()
        )
        await handler.handle(
            DeleteSKUCommand(
                product_id=product.id,
                sku_id=sku.id,
            )
        )

        sku_deleted_events = [
            e for e in uow.collected_events if isinstance(e, SKUDeletedEvent)
        ]
        assert len(sku_deleted_events) == 1
        assert sku_deleted_events[0].sku_id == sku.id
        assert sku_deleted_events[0].product_id == product.id
        assert sku_deleted_events[0].variant_id == variant_id


# ============================================================================
# TestGenerateSKUMatrix
# ============================================================================


class TestGenerateSKUMatrix:
    """Tests for GenerateSKUMatrixHandler."""

    def _make_handler(self, uow):
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

    async def test_happy_path_single_attribute_two_values(self):
        uow = FakeUnitOfWork()
        product, template, attr, values = _seed_product_with_template(uow)
        variant_id = product.variants[0].id

        handler = self._make_handler(uow)
        result = await handler.handle(
            GenerateSKUMatrixCommand(
                product_id=product.id,
                variant_id=variant_id,
                attribute_selections=[
                    AttributeSelection(
                        attribute_id=attr.id,
                        value_ids=[values[0].id, values[1].id],
                    )
                ],
            )
        )

        assert isinstance(result, GenerateSKUMatrixResult)
        assert result.created_count == 2
        assert result.skipped_count == 0
        assert len(result.sku_ids) == 2
        assert uow.committed is True

    async def test_happy_path_two_attributes_cartesian(self):
        uow = FakeUnitOfWork()
        product, template, attr1, values1 = _seed_product_with_template(uow)
        variant_id = product.variants[0].id

        # Create a second attribute with 2 values
        attr2 = Attribute.create(
            code="color",
            slug="color",
            name_i18n={"en": "Color", "ru": "Цвет"},
            data_type=AttributeDataType.STRING,
            ui_type=AttributeUIType.COLOR_SWATCH,
            level=AttributeLevel.VARIANT,
            is_dictionary=True,
            group_id=None,
        )
        uow.attributes._store[attr2.id] = attr2

        val_white = AttributeValue.create(
            attribute_id=attr2.id,
            code="white",
            slug="white",
            value_i18n={"en": "White", "ru": "Белый"},
        )
        val_black = AttributeValue.create(
            attribute_id=attr2.id,
            code="black",
            slug="black",
            value_i18n={"en": "Black", "ru": "Черный"},
        )
        uow.attribute_values._store[val_white.id] = val_white
        uow.attribute_values._store[val_black.id] = val_black

        binding2 = TemplateAttributeBinding.create(
            template_id=template.id,
            attribute_id=attr2.id,
        )
        uow.template_bindings._store[binding2.id] = binding2

        handler = self._make_handler(uow)
        result = await handler.handle(
            GenerateSKUMatrixCommand(
                product_id=product.id,
                variant_id=variant_id,
                attribute_selections=[
                    AttributeSelection(
                        attribute_id=attr1.id,
                        value_ids=[values1[0].id, values1[1].id],
                    ),
                    AttributeSelection(
                        attribute_id=attr2.id,
                        value_ids=[val_white.id, val_black.id],
                    ),
                ],
            )
        )

        assert result.created_count == 4  # 2 x 2 cartesian product
        assert result.skipped_count == 0
        assert len(result.sku_ids) == 4
        assert uow.committed is True

    async def test_skips_duplicate_combinations(self):
        uow = FakeUnitOfWork()
        product, template, attr, values = _seed_product_with_template(uow)
        variant_id = product.variants[0].id

        # Pre-add a SKU with the variant attributes of value[0]
        product.add_sku(
            variant_id=variant_id,
            sku_code="EXISTING-SKU",
            variant_attributes=[(attr.id, values[0].id)],
        )
        product.clear_domain_events()
        uow.products._store[product.id] = product

        handler = self._make_handler(uow)
        result = await handler.handle(
            GenerateSKUMatrixCommand(
                product_id=product.id,
                variant_id=variant_id,
                attribute_selections=[
                    AttributeSelection(
                        attribute_id=attr.id,
                        value_ids=[values[0].id, values[1].id],
                    )
                ],
            )
        )

        # One should be created, one should be skipped (the existing combo)
        assert result.skipped_count >= 1
        assert result.created_count + result.skipped_count == 2
        assert uow.committed is True

    async def test_product_not_found(self):
        uow = FakeUnitOfWork()

        handler = self._make_handler(uow)
        with pytest.raises(ProductNotFoundError):
            await handler.handle(
                GenerateSKUMatrixCommand(
                    product_id=uuid.uuid4(),
                    variant_id=uuid.uuid4(),
                    attribute_selections=[],
                )
            )
        assert uow.committed is False

    async def test_attribute_not_found(self):
        uow = FakeUnitOfWork()
        product, template, attr, values = _seed_product_with_template(uow)

        handler = self._make_handler(uow)
        fake_attr_id = uuid.uuid4()
        with pytest.raises(AttributeNotFoundError):
            await handler.handle(
                GenerateSKUMatrixCommand(
                    product_id=product.id,
                    variant_id=product.variants[0].id,
                    attribute_selections=[
                        AttributeSelection(
                            attribute_id=fake_attr_id,
                            value_ids=[uuid.uuid4()],
                        )
                    ],
                )
            )
        assert uow.committed is False

    async def test_attribute_wrong_level_not_variant(self):
        uow = FakeUnitOfWork()
        product, template, attr, values = _seed_product_with_template(uow)

        # Create a PRODUCT-level attribute
        product_attr = Attribute.create(
            code="material",
            slug="material",
            name_i18n={"en": "Material", "ru": "Материал"},
            data_type=AttributeDataType.STRING,
            ui_type=AttributeUIType.TEXT_BUTTON,
            level=AttributeLevel.PRODUCT,
            is_dictionary=True,
            group_id=None,
        )
        uow.attributes._store[product_attr.id] = product_attr

        # Bind it to the template
        binding_prod = TemplateAttributeBinding.create(
            template_id=template.id,
            attribute_id=product_attr.id,
        )
        uow.template_bindings._store[binding_prod.id] = binding_prod

        handler = self._make_handler(uow)
        with pytest.raises(AttributeLevelMismatchError):
            await handler.handle(
                GenerateSKUMatrixCommand(
                    product_id=product.id,
                    variant_id=product.variants[0].id,
                    attribute_selections=[
                        AttributeSelection(
                            attribute_id=product_attr.id,
                            value_ids=[uuid.uuid4()],
                        )
                    ],
                )
            )
        assert uow.committed is False

    async def test_attribute_value_not_found(self):
        uow = FakeUnitOfWork()
        product, template, attr, values = _seed_product_with_template(uow)

        handler = self._make_handler(uow)
        fake_value_id = uuid.uuid4()
        with pytest.raises(AttributeValueNotFoundError):
            await handler.handle(
                GenerateSKUMatrixCommand(
                    product_id=product.id,
                    variant_id=product.variants[0].id,
                    attribute_selections=[
                        AttributeSelection(
                            attribute_id=attr.id,
                            value_ids=[fake_value_id],
                        )
                    ],
                )
            )
        assert uow.committed is False
