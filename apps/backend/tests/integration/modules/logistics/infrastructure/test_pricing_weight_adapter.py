"""Integration tests for ``PricingWeightAdapter`` (real DB).

Walks the full SKU → Product → Supplier → CategoryPricingSettings chain
on a real PostgreSQL session to prove that the adapter:

1. Returns the per-category override when a ``CategoryPricingSettings``
   row exists for the SKU's category and the supplier-type's pricing
   context.
2. Falls back to ``Variable[code="weight_g"].default_value`` when no
   override is configured.
3. Falls back when the supplier-type → context mapping is missing.
4. Skips unknown SKUs gracefully (omitted from the result map).
5. Treats zero / negative stored weights as missing (defensive guard
   against misconfiguration that would otherwise feed ``weight=0`` into
   CDEK / Yandex and get the parcel rejected).
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.domain.entities import Product
from src.modules.catalog.domain.value_objects import ProductStatus, SkuPricingStatus
from src.modules.catalog.infrastructure.models import (
    SKU as SKUModel,
)
from src.modules.catalog.infrastructure.models import (
    Brand as BrandModel,
)
from src.modules.catalog.infrastructure.models import (
    Category as CategoryModel,
)
from src.modules.catalog.infrastructure.models import (
    Product as ProductModel,
)
from src.modules.catalog.infrastructure.models import (
    ProductVariant as ProductVariantModel,
)
from src.modules.logistics.infrastructure.adapters.pricing_weight_adapter import (
    WEIGHT_VARIABLE_CODE,
    PricingWeightAdapter,
)
from src.modules.pricing.infrastructure.models import (
    CategoryPricingSettingsModel,
    PricingContextModel,
    SupplierTypeContextMappingModel,
    VariableModel,
)
from src.modules.supplier.infrastructure.models import Supplier as SupplierModel

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Test doubles
# ---------------------------------------------------------------------------


class _NullLogger:
    """Minimal ILogger stub — these tests don't assert on log output."""

    def bind(self, **_: Any) -> _NullLogger:
        return self

    def info(self, *_: Any, **__: Any) -> None: ...
    def warning(self, *_: Any, **__: Any) -> None: ...
    def error(self, *_: Any, **__: Any) -> None: ...
    def critical(self, *_: Any, **__: Any) -> None: ...
    def debug(self, *_: Any, **__: Any) -> None: ...
    def exception(self, *_: Any, **__: Any) -> None: ...


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
async def _seed_geo(db_session: AsyncSession) -> None:
    await db_session.execute(
        text(
            "INSERT INTO countries (alpha2, alpha3, numeric) "
            "VALUES ('RU', 'RUS', '643'), ('CN', 'CHN', '156') "
            "ON CONFLICT (alpha2) DO NOTHING"
        )
    )
    await db_session.execute(
        text(
            "INSERT INTO currencies (code, numeric, name, minor_unit) "
            "VALUES ('RUB', '643', 'Russian Ruble', 2) "
            "ON CONFLICT (code) DO NOTHING"
        )
    )
    await db_session.flush()


@pytest.fixture()
async def system_weight_variable(db_session: AsyncSession) -> VariableModel:
    """Mirror the seed entry for the ``weight_g`` system variable."""
    variable = VariableModel(
        id=uuid.uuid4(),
        code=WEIGHT_VARIABLE_CODE,
        scope="category",
        data_type="integer",
        unit="G",
        name={"ru": "Вес", "en": "Weight"},
        description={},
        is_required=True,
        default_value=Decimal("500"),
        is_system=True,
        is_fx_rate=False,
    )
    db_session.add(variable)
    await db_session.flush()
    return variable


@pytest.fixture()
async def cross_border_supplier(db_session: AsyncSession) -> SupplierModel:
    supplier = SupplierModel(
        id=uuid.uuid4(),
        name="Poizon",
        type="cross_border",
        country_code="CN",
    )
    db_session.add(supplier)
    await db_session.flush()
    return supplier


@pytest.fixture()
async def cross_border_context(db_session: AsyncSession) -> PricingContextModel:
    context = PricingContextModel(
        id=uuid.uuid4(),
        code=f"checkout-{uuid.uuid4().hex[:8]}",
        name={"ru": "Кросс-бордер", "en": "Cross-border"},
        rounding_mode="HALF_UP",
        rounding_step=Decimal("0.01"),
        margin_floor_pct=Decimal("0"),
        evaluation_timeout_ms=50,
        simulation_threshold=0,
        global_values={},
        global_values_set_at={},
        is_active=True,
    )
    db_session.add(context)
    await db_session.flush()
    return context


@pytest.fixture()
async def supplier_type_mapping(
    db_session: AsyncSession,
    cross_border_context: PricingContextModel,
) -> SupplierTypeContextMappingModel:
    mapping = SupplierTypeContextMappingModel(
        id=uuid.uuid4(),
        supplier_type="cross_border",
        context_id=cross_border_context.id,
    )
    db_session.add(mapping)
    await db_session.flush()
    return mapping


async def _seed_brand(db_session: AsyncSession) -> BrandModel:
    suffix = uuid.uuid4().hex[:8]
    brand = BrandModel(
        id=uuid.uuid4(),
        slug=f"brand-{suffix}",
        name=f"Brand {suffix}",
    )
    db_session.add(brand)
    await db_session.flush()
    return brand


async def _seed_category(db_session: AsyncSession) -> CategoryModel:
    slug = f"cat-{uuid.uuid4().hex[:8]}"
    category = CategoryModel(
        id=uuid.uuid4(),
        slug=slug,
        full_slug=slug,
        level=0,
        name_i18n={"ru": "Категория", "en": "Category"},
        sort_order=0,
    )
    db_session.add(category)
    await db_session.flush()
    return category


async def _seed_sku(
    db_session: AsyncSession,
    *,
    category_id: uuid.UUID,
    supplier_id: uuid.UUID,
) -> uuid.UUID:
    """Persist a minimal Product → Variant → SKU triplet, returning the SKU id.

    Goes through ``Product.create`` so the auto-attached default variant is
    materialised; we then add a SKU directly via ORM (bypassing the
    repository to keep this test focused on the weight adapter).
    """
    brand = await _seed_brand(db_session)
    product_aggregate = Product.create(
        slug=f"product-{uuid.uuid4().hex[:8]}",
        title_i18n={"ru": "Тест", "en": "Test"},
        brand_id=brand.id,
        primary_category_id=category_id,
    )
    default_variant = product_aggregate.variants[0]

    product_row = ProductModel(
        id=product_aggregate.id,
        primary_category_id=category_id,
        brand_id=brand.id,
        supplier_id=supplier_id,
        slug=product_aggregate.slug,
        title_i18n=product_aggregate.title_i18n,
        description_i18n={},
        attributes={},
        tags=[],
        status=ProductStatus.DRAFT,
        is_visible=True,
    )
    db_session.add(product_row)

    variant_row = ProductVariantModel(
        id=default_variant.id,
        product_id=product_aggregate.id,
        name_i18n={"ru": "Базовый", "en": "Default"},
        sort_order=0,
        default_currency="RUB",
    )
    db_session.add(variant_row)
    await db_session.flush()

    sku_id = uuid.uuid4()
    sku_row = SKUModel(
        id=sku_id,
        product_id=product_aggregate.id,
        variant_id=default_variant.id,
        sku_code=f"SKU-{sku_id.hex[:8]}",
        variant_hash=uuid.uuid4().hex,
        attributes_cache={},
        is_active=True,
        currency="RUB",
        pricing_status=SkuPricingStatus.LEGACY,
    )
    db_session.add(sku_row)
    await db_session.flush()
    return sku_id


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_returns_category_override_when_present(
    db_session: AsyncSession,
    system_weight_variable: VariableModel,
    cross_border_supplier: SupplierModel,
    cross_border_context: PricingContextModel,
    supplier_type_mapping: SupplierTypeContextMappingModel,
) -> None:
    del system_weight_variable, supplier_type_mapping
    category = await _seed_category(db_session)
    sku_id = await _seed_sku(
        db_session,
        category_id=category.id,
        supplier_id=cross_border_supplier.id,
    )
    db_session.add(
        CategoryPricingSettingsModel(
            id=uuid.uuid4(),
            category_id=category.id,
            context_id=cross_border_context.id,
            values={WEIGHT_VARIABLE_CODE: "850"},
            ranges=[],
            explicit_no_ranges=False,
        )
    )
    await db_session.flush()

    adapter = PricingWeightAdapter(session=db_session, logger=_NullLogger())
    weights = await adapter.resolve_weight_grams([sku_id])

    assert weights == {sku_id: 850}


async def test_falls_back_to_variable_default_when_category_has_no_override(
    db_session: AsyncSession,
    system_weight_variable: VariableModel,
    cross_border_supplier: SupplierModel,
    supplier_type_mapping: SupplierTypeContextMappingModel,
) -> None:
    del system_weight_variable, supplier_type_mapping
    category = await _seed_category(db_session)
    sku_id = await _seed_sku(
        db_session,
        category_id=category.id,
        supplier_id=cross_border_supplier.id,
    )

    adapter = PricingWeightAdapter(session=db_session, logger=_NullLogger())
    weights = await adapter.resolve_weight_grams([sku_id])

    assert weights == {sku_id: 500}


async def test_falls_back_when_supplier_type_mapping_missing(
    db_session: AsyncSession,
    system_weight_variable: VariableModel,
    cross_border_supplier: SupplierModel,
    cross_border_context: PricingContextModel,
) -> None:
    """Without a supplier_type → context row we cannot pick category settings."""
    del system_weight_variable
    category = await _seed_category(db_session)
    db_session.add(
        CategoryPricingSettingsModel(
            id=uuid.uuid4(),
            category_id=category.id,
            context_id=cross_border_context.id,
            values={WEIGHT_VARIABLE_CODE: "850"},
            ranges=[],
            explicit_no_ranges=False,
        )
    )
    sku_id = await _seed_sku(
        db_session,
        category_id=category.id,
        supplier_id=cross_border_supplier.id,
    )
    await db_session.flush()

    adapter = PricingWeightAdapter(session=db_session, logger=_NullLogger())
    weights = await adapter.resolve_weight_grams([sku_id])

    # No mapping → adapter cannot resolve which context owns the category
    # override → defaults must kick in.
    assert weights == {sku_id: 500}


async def test_unknown_sku_omitted_from_result(
    db_session: AsyncSession,
    system_weight_variable: VariableModel,
) -> None:
    del system_weight_variable

    adapter = PricingWeightAdapter(session=db_session, logger=_NullLogger())
    weights = await adapter.resolve_weight_grams([uuid.uuid4()])

    assert weights == {}


async def test_zero_or_negative_stored_weight_falls_back_to_default(
    db_session: AsyncSession,
    system_weight_variable: VariableModel,
    cross_border_supplier: SupplierModel,
    cross_border_context: PricingContextModel,
    supplier_type_mapping: SupplierTypeContextMappingModel,
) -> None:
    del system_weight_variable, supplier_type_mapping
    category = await _seed_category(db_session)
    sku_id = await _seed_sku(
        db_session,
        category_id=category.id,
        supplier_id=cross_border_supplier.id,
    )
    db_session.add(
        CategoryPricingSettingsModel(
            id=uuid.uuid4(),
            category_id=category.id,
            context_id=cross_border_context.id,
            values={WEIGHT_VARIABLE_CODE: "0"},
            ranges=[],
            explicit_no_ranges=False,
        )
    )
    await db_session.flush()

    adapter = PricingWeightAdapter(session=db_session, logger=_NullLogger())
    weights = await adapter.resolve_weight_grams([sku_id])

    # Zero would let CDEK reject the parcel — must fall back to system default.
    assert weights == {sku_id: 500}


async def test_batch_resolution_mixes_overrides_and_defaults(
    db_session: AsyncSession,
    system_weight_variable: VariableModel,
    cross_border_supplier: SupplierModel,
    cross_border_context: PricingContextModel,
    supplier_type_mapping: SupplierTypeContextMappingModel,
) -> None:
    del system_weight_variable, supplier_type_mapping
    cat_with = await _seed_category(db_session)
    cat_without = await _seed_category(db_session)
    sku_with = await _seed_sku(
        db_session, category_id=cat_with.id, supplier_id=cross_border_supplier.id
    )
    sku_without = await _seed_sku(
        db_session, category_id=cat_without.id, supplier_id=cross_border_supplier.id
    )
    db_session.add(
        CategoryPricingSettingsModel(
            id=uuid.uuid4(),
            category_id=cat_with.id,
            context_id=cross_border_context.id,
            values={WEIGHT_VARIABLE_CODE: "1200"},
            ranges=[],
            explicit_no_ranges=False,
        )
    )
    await db_session.flush()

    adapter = PricingWeightAdapter(session=db_session, logger=_NullLogger())
    weights = await adapter.resolve_weight_grams([sku_with, sku_without])

    assert weights == {sku_with: 1200, sku_without: 500}
