# tests/unit/modules/catalog/application/queries/test_get_product.py
"""Unit tests for GetProductHandler query handler.

Covers:
- Happy path: product found with SKUs and computed min/max prices.
- Not found: ProductNotFoundError raised when product does not exist.
- SKU mapping: ORM SKU -> SKUReadModel including variant attributes
  and compare_at_price.
- Price aggregation: min_price/max_price computed across active,
  non-deleted SKUs only.
- Edge cases: no SKUs, all SKUs deleted, all SKUs inactive,
  mixed active/inactive/deleted SKUs.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.modules.catalog.application.queries.get_product import GetProductHandler
from src.modules.catalog.application.queries.read_models import (
    MoneyReadModel,
    ProductReadModel,
    ProductVariantReadModel,
    SKUReadModel,
    VariantAttributePairReadModel,
)
from src.modules.catalog.domain.exceptions import ProductNotFoundError

pytestmark = pytest.mark.unit

_NOW = datetime(2026, 3, 18, 12, 0, 0, tzinfo=UTC)
_LATER = datetime(2026, 3, 18, 13, 0, 0, tzinfo=UTC)


# ---------------------------------------------------------------------------
# Helpers: lightweight fakes that mimic ORM model attribute access
# ---------------------------------------------------------------------------


def _make_sku_link(
    attribute_id: uuid.UUID | None = None,
    attribute_value_id: uuid.UUID | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        attribute_id=attribute_id or uuid.uuid4(),
        attribute_value_id=attribute_value_id or uuid.uuid4(),
    )


def _make_orm_sku(
    product_id: uuid.UUID,
    price: int = 1000,
    compare_at_price: int | None = None,
    currency: str = "USD",
    is_active: bool = True,
    deleted_at: datetime | None = None,
    attribute_values: list[SimpleNamespace] | None = None,
    variant_id: uuid.UUID | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        product_id=product_id,
        variant_id=variant_id or uuid.uuid4(),
        sku_code=f"SKU-{uuid.uuid4().hex[:6]}",
        variant_hash=uuid.uuid4().hex[:12],
        price=price,
        compare_at_price=compare_at_price,
        currency=currency,
        is_active=is_active,
        version=1,
        deleted_at=deleted_at,
        created_at=_NOW,
        updated_at=_NOW,
        attribute_values=attribute_values or [],
    )


def _make_orm_variant(
    product_id: uuid.UUID,
    skus: list[SimpleNamespace] | None = None,
    default_price: int | None = None,
    default_currency: str = "USD",
    deleted_at: datetime | None = None,
) -> SimpleNamespace:
    vid = uuid.uuid4()
    variant_skus = skus or []
    # Set variant_id on each SKU
    for s in variant_skus:
        s.variant_id = vid
    return SimpleNamespace(
        id=vid,
        product_id=product_id,
        name_i18n={"en": "Default Variant"},
        description_i18n=None,
        sort_order=0,
        default_price=default_price,
        default_currency=default_currency,
        deleted_at=deleted_at,
        created_at=_NOW,
        updated_at=_NOW,
        skus=variant_skus,
    )


class _FakeStatus:
    """Mimics an enum with a .value property (like ORM ProductStatus)."""

    def __init__(self, value: str) -> None:
        self.value = value


def _make_orm_product(
    product_id: uuid.UUID | None = None,
    variants: list[SimpleNamespace] | None = None,
    status: str = "draft",
    tags: list[str] | None = None,
    # Legacy helper: wraps skus in a single default variant for easy migration
    skus: list[SimpleNamespace] | None = None,
) -> SimpleNamespace:
    pid = product_id or uuid.uuid4()
    if variants is None and skus is not None:
        # Wrap bare skus in a single default variant for backward compat
        variants = [_make_orm_variant(pid, skus=skus)]
    return SimpleNamespace(
        id=pid,
        slug="test-product",
        title_i18n={"en": "Test Product"},
        description_i18n={"en": "A test product"},
        status=_FakeStatus(status),
        brand_id=uuid.uuid4(),
        primary_category_id=uuid.uuid4(),
        supplier_id=None,
        country_of_origin=None,
        tags=tags or ["tag1"],
        version=1,
        deleted_at=None,
        created_at=_NOW,
        updated_at=_NOW,
        published_at=None,
        variants=variants or [],
    )


def _mock_session(orm_product: SimpleNamespace | None) -> AsyncMock:
    """Build an AsyncSession mock whose execute().scalar_one_or_none() returns orm_product."""
    session = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = orm_product
    session.execute.return_value = result_mock
    return session


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestGetProductHandlerHappyPath:
    """Happy path: product exists and is returned with correct mapping."""

    @pytest.mark.asyncio
    async def test_returns_product_read_model(self) -> None:
        """Handler returns a ProductReadModel for an existing product."""
        pid = uuid.uuid4()
        orm = _make_orm_product(product_id=pid)
        session = _mock_session(orm)

        handler = GetProductHandler(session)
        result = await handler.handle(pid)

        assert isinstance(result, ProductReadModel)
        assert result.id == pid
        assert result.slug == "test-product"

    @pytest.mark.asyncio
    async def test_session_execute_called(self) -> None:
        """Handler calls session.execute exactly once."""
        pid = uuid.uuid4()
        orm = _make_orm_product(product_id=pid)
        session = _mock_session(orm)

        handler = GetProductHandler(session)
        await handler.handle(pid)

        session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_status_is_plain_string(self) -> None:
        """Returned status is a plain string, not an enum."""
        pid = uuid.uuid4()
        orm = _make_orm_product(product_id=pid, status="published")
        session = _mock_session(orm)

        handler = GetProductHandler(session)
        result = await handler.handle(pid)

        assert result.status == "published"
        assert type(result.status) is str

    @pytest.mark.asyncio
    async def test_tags_copied_as_list(self) -> None:
        """Tags are returned as a plain list."""
        pid = uuid.uuid4()
        orm = _make_orm_product(product_id=pid, tags=["electronics", "sale"])
        session = _mock_session(orm)

        handler = GetProductHandler(session)
        result = await handler.handle(pid)

        assert result.tags == ["electronics", "sale"]

    @pytest.mark.asyncio
    async def test_empty_tags_returns_empty_list(self) -> None:
        """None tags returns an empty list."""
        pid = uuid.uuid4()
        orm = _make_orm_product(product_id=pid, tags=None)
        # tags=None should result in []
        orm.tags = None
        session = _mock_session(orm)

        handler = GetProductHandler(session)
        result = await handler.handle(pid)

        assert result.tags == []

    @pytest.mark.asyncio
    async def test_attributes_list_empty_until_mt16(self) -> None:
        """Attributes list is empty until MT-16 ORM model exists."""
        pid = uuid.uuid4()
        orm = _make_orm_product(product_id=pid)
        session = _mock_session(orm)

        handler = GetProductHandler(session)
        result = await handler.handle(pid)

        assert result.attributes == []


class TestGetProductHandlerNotFound:
    """Not found: product does not exist raises ProductNotFoundError."""

    @pytest.mark.asyncio
    async def test_raises_product_not_found_error(self) -> None:
        """Handler raises ProductNotFoundError when product is missing."""
        pid = uuid.uuid4()
        session = _mock_session(None)

        handler = GetProductHandler(session)
        with pytest.raises(ProductNotFoundError):
            await handler.handle(pid)


class TestGetProductHandlerVariantAndSKUMapping:
    """Variant + SKU mapping: ORM variant/SKU -> read models with correct fields."""

    @pytest.mark.asyncio
    async def test_variants_mapped_to_read_models(self) -> None:
        """Each ORM variant is mapped to a ProductVariantReadModel."""
        pid = uuid.uuid4()
        sku1 = _make_orm_sku(pid, price=500)
        sku2 = _make_orm_sku(pid, price=1500)
        orm = _make_orm_product(product_id=pid, skus=[sku1, sku2])
        session = _mock_session(orm)

        handler = GetProductHandler(session)
        result = await handler.handle(pid)

        assert len(result.variants) == 1
        assert isinstance(result.variants[0], ProductVariantReadModel)
        assert len(result.variants[0].skus) == 2
        assert all(isinstance(s, SKUReadModel) for s in result.variants[0].skus)

    @pytest.mark.asyncio
    async def test_sku_price_is_money_read_model(self) -> None:
        """SKU price is wrapped in MoneyReadModel."""
        pid = uuid.uuid4()
        sku = _make_orm_sku(pid, price=2999, currency="EUR")
        orm = _make_orm_product(product_id=pid, skus=[sku])
        session = _mock_session(orm)

        handler = GetProductHandler(session)
        result = await handler.handle(pid)

        sku_rm = result.variants[0].skus[0]
        assert isinstance(sku_rm.price, MoneyReadModel)
        assert sku_rm.price.amount == 2999
        assert sku_rm.price.currency == "EUR"

    @pytest.mark.asyncio
    async def test_sku_compare_at_price_none(self) -> None:
        """SKU with no compare_at_price maps to None."""
        pid = uuid.uuid4()
        sku = _make_orm_sku(pid, compare_at_price=None)
        orm = _make_orm_product(product_id=pid, skus=[sku])
        session = _mock_session(orm)

        handler = GetProductHandler(session)
        result = await handler.handle(pid)

        assert result.variants[0].skus[0].compare_at_price is None

    @pytest.mark.asyncio
    async def test_sku_compare_at_price_set(self) -> None:
        """SKU with compare_at_price maps to MoneyReadModel."""
        pid = uuid.uuid4()
        sku = _make_orm_sku(pid, price=1000, compare_at_price=1500, currency="USD")
        orm = _make_orm_product(product_id=pid, skus=[sku])
        session = _mock_session(orm)

        handler = GetProductHandler(session)
        result = await handler.handle(pid)

        sku_rm = result.variants[0].skus[0]
        assert sku_rm.compare_at_price is not None
        assert sku_rm.compare_at_price.amount == 1500
        assert sku_rm.compare_at_price.currency == "USD"

    @pytest.mark.asyncio
    async def test_sku_variant_attributes_mapped(self) -> None:
        """SKU variant attribute links are mapped to VariantAttributePairReadModel."""
        pid = uuid.uuid4()
        attr_id = uuid.uuid4()
        val_id = uuid.uuid4()
        link = _make_sku_link(attribute_id=attr_id, attribute_value_id=val_id)
        sku = _make_orm_sku(pid, attribute_values=[link])
        orm = _make_orm_product(product_id=pid, skus=[sku])
        session = _mock_session(orm)

        handler = GetProductHandler(session)
        result = await handler.handle(pid)

        sku_rm = result.variants[0].skus[0]
        assert len(sku_rm.variant_attributes) == 1
        pair = sku_rm.variant_attributes[0]
        assert isinstance(pair, VariantAttributePairReadModel)
        assert pair.attribute_id == attr_id
        assert pair.attribute_value_id == val_id


class TestGetProductHandlerPriceAggregation:
    """Price aggregation: min_price/max_price across active non-deleted SKUs."""

    @pytest.mark.asyncio
    async def test_min_max_price_computed(self) -> None:
        """min_price and max_price reflect active, non-deleted SKUs."""
        pid = uuid.uuid4()
        sku1 = _make_orm_sku(pid, price=500, is_active=True)
        sku2 = _make_orm_sku(pid, price=2000, is_active=True)
        sku3 = _make_orm_sku(pid, price=1000, is_active=True)
        orm = _make_orm_product(product_id=pid, skus=[sku1, sku2, sku3])
        session = _mock_session(orm)

        handler = GetProductHandler(session)
        result = await handler.handle(pid)

        assert result.min_price == 500
        assert result.max_price == 2000

    @pytest.mark.asyncio
    async def test_no_skus_gives_none_prices(self) -> None:
        """No SKUs: min_price and max_price are None."""
        pid = uuid.uuid4()
        orm = _make_orm_product(product_id=pid, skus=[])
        session = _mock_session(orm)

        handler = GetProductHandler(session)
        result = await handler.handle(pid)

        assert result.min_price is None
        assert result.max_price is None

    @pytest.mark.asyncio
    async def test_inactive_skus_excluded_from_prices(self) -> None:
        """Inactive SKUs are excluded from price aggregation."""
        pid = uuid.uuid4()
        active_sku = _make_orm_sku(pid, price=1000, is_active=True)
        inactive_sku = _make_orm_sku(pid, price=500, is_active=False)
        orm = _make_orm_product(product_id=pid, skus=[active_sku, inactive_sku])
        session = _mock_session(orm)

        handler = GetProductHandler(session)
        result = await handler.handle(pid)

        assert result.min_price == 1000
        assert result.max_price == 1000

    @pytest.mark.asyncio
    async def test_deleted_skus_excluded_from_prices(self) -> None:
        """Deleted SKUs are excluded from price aggregation."""
        pid = uuid.uuid4()
        active_sku = _make_orm_sku(pid, price=2000, is_active=True)
        deleted_sku = _make_orm_sku(pid, price=100, is_active=True, deleted_at=_LATER)
        orm = _make_orm_product(product_id=pid, skus=[active_sku, deleted_sku])
        session = _mock_session(orm)

        handler = GetProductHandler(session)
        result = await handler.handle(pid)

        assert result.min_price == 2000
        assert result.max_price == 2000

    @pytest.mark.asyncio
    async def test_all_skus_inactive_gives_none_prices(self) -> None:
        """All inactive SKUs: min_price and max_price are None."""
        pid = uuid.uuid4()
        sku1 = _make_orm_sku(pid, price=500, is_active=False)
        sku2 = _make_orm_sku(pid, price=1000, is_active=False)
        orm = _make_orm_product(product_id=pid, skus=[sku1, sku2])
        session = _mock_session(orm)

        handler = GetProductHandler(session)
        result = await handler.handle(pid)

        assert result.min_price is None
        assert result.max_price is None

    @pytest.mark.asyncio
    async def test_single_active_sku_min_equals_max(self) -> None:
        """Single active SKU: min_price equals max_price."""
        pid = uuid.uuid4()
        sku = _make_orm_sku(pid, price=750, is_active=True)
        orm = _make_orm_product(product_id=pid, skus=[sku])
        session = _mock_session(orm)

        handler = GetProductHandler(session)
        result = await handler.handle(pid)

        assert result.min_price == 750
        assert result.max_price == 750
