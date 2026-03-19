# tests/unit/modules/catalog/application/queries/test_list_skus.py
"""Unit tests for ListSKUsHandler query handler.

Covers:
- Happy path: SKUs returned for a product with correct mapping.
- Empty result: no SKUs for a product returns empty list.
- SKU mapping: price, compare_at_price, variant attributes.
- ListSKUsQuery dataclass: product_id required, frozen.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.modules.catalog.application.queries.list_skus import (
    ListSKUsHandler,
    ListSKUsQuery,
)
from src.modules.catalog.application.queries.read_models import (
    MoneyReadModel,
    SKUReadModel,
    VariantAttributePairReadModel,
)

pytestmark = pytest.mark.unit

_NOW = datetime(2026, 3, 18, 12, 0, 0, tzinfo=UTC)


# ---------------------------------------------------------------------------
# Helpers
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
    sku_code: str | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        product_id=product_id,
        sku_code=sku_code or f"SKU-{uuid.uuid4().hex[:6]}",
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


def _mock_session(orm_rows: list[SimpleNamespace]) -> AsyncMock:
    """Build an AsyncSession mock returning scalars().all() -> orm_rows."""
    session = AsyncMock()
    result_mock = MagicMock()
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = orm_rows
    result_mock.scalars.return_value = scalars_mock
    session.execute.return_value = result_mock
    return session


# ---------------------------------------------------------------------------
# Tests: ListSKUsQuery
# ---------------------------------------------------------------------------


class TestListSKUsQuery:
    """Tests for ListSKUsQuery frozen dataclass."""

    def test_product_id_required(self) -> None:
        """product_id is a required field."""
        pid = uuid.uuid4()
        query = ListSKUsQuery(product_id=pid)
        assert query.product_id == pid

    def test_frozen_immutable(self) -> None:
        """ListSKUsQuery is frozen (immutable)."""
        query = ListSKUsQuery(product_id=uuid.uuid4())
        with pytest.raises(AttributeError):
            query.product_id = uuid.uuid4()  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Tests: ListSKUsHandler
# ---------------------------------------------------------------------------


class TestListSKUsHandlerHappyPath:
    """Happy path: SKUs found and returned as list of SKUReadModel."""

    @pytest.mark.asyncio
    async def test_returns_list_of_sku_read_models(self) -> None:
        """Handler returns a list of SKUReadModel."""
        pid = uuid.uuid4()
        sku1 = _make_orm_sku(pid, price=500)
        sku2 = _make_orm_sku(pid, price=1500)
        session = _mock_session([sku1, sku2])

        handler = ListSKUsHandler(session)
        result = await handler.handle(ListSKUsQuery(product_id=pid))

        assert isinstance(result, list)
        assert len(result) == 2
        assert all(isinstance(s, SKUReadModel) for s in result)

    @pytest.mark.asyncio
    async def test_session_execute_called_once(self) -> None:
        """Handler calls session.execute exactly once."""
        pid = uuid.uuid4()
        session = _mock_session([])

        handler = ListSKUsHandler(session)
        await handler.handle(ListSKUsQuery(product_id=pid))

        session.execute.assert_awaited_once()


class TestListSKUsHandlerEmptyResult:
    """Edge case: no SKUs for the product."""

    @pytest.mark.asyncio
    async def test_empty_list_returned(self) -> None:
        """No SKUs returns an empty list."""
        pid = uuid.uuid4()
        session = _mock_session([])

        handler = ListSKUsHandler(session)
        result = await handler.handle(ListSKUsQuery(product_id=pid))

        assert result == []


class TestListSKUsHandlerMapping:
    """SKU mapping: ORM -> read model fields."""

    @pytest.mark.asyncio
    async def test_price_wrapped_in_money_read_model(self) -> None:
        """Price is wrapped in MoneyReadModel with amount and currency."""
        pid = uuid.uuid4()
        sku = _make_orm_sku(pid, price=2500, currency="EUR")
        session = _mock_session([sku])

        handler = ListSKUsHandler(session)
        result = await handler.handle(ListSKUsQuery(product_id=pid))

        assert isinstance(result[0].price, MoneyReadModel)
        assert result[0].price.amount == 2500
        assert result[0].price.currency == "EUR"

    @pytest.mark.asyncio
    async def test_compare_at_price_none_when_absent(self) -> None:
        """compare_at_price is None when ORM value is None."""
        pid = uuid.uuid4()
        sku = _make_orm_sku(pid, compare_at_price=None)
        session = _mock_session([sku])

        handler = ListSKUsHandler(session)
        result = await handler.handle(ListSKUsQuery(product_id=pid))

        assert result[0].compare_at_price is None

    @pytest.mark.asyncio
    async def test_compare_at_price_mapped_when_present(self) -> None:
        """compare_at_price is MoneyReadModel when ORM value is set."""
        pid = uuid.uuid4()
        sku = _make_orm_sku(pid, price=1000, compare_at_price=1500, currency="USD")
        session = _mock_session([sku])

        handler = ListSKUsHandler(session)
        result = await handler.handle(ListSKUsQuery(product_id=pid))

        assert result[0].compare_at_price is not None
        assert result[0].compare_at_price.amount == 1500
        assert result[0].compare_at_price.currency == "USD"

    @pytest.mark.asyncio
    async def test_variant_attributes_mapped(self) -> None:
        """Variant attribute links are mapped to VariantAttributePairReadModel."""
        pid = uuid.uuid4()
        attr_id = uuid.uuid4()
        val_id = uuid.uuid4()
        link = _make_sku_link(attribute_id=attr_id, attribute_value_id=val_id)
        sku = _make_orm_sku(pid, attribute_values=[link])
        session = _mock_session([sku])

        handler = ListSKUsHandler(session)
        result = await handler.handle(ListSKUsQuery(product_id=pid))

        assert len(result[0].variant_attributes) == 1
        pair = result[0].variant_attributes[0]
        assert isinstance(pair, VariantAttributePairReadModel)
        assert pair.attribute_id == attr_id
        assert pair.attribute_value_id == val_id

    @pytest.mark.asyncio
    async def test_multiple_variant_attributes(self) -> None:
        """Multiple variant attribute links are all mapped."""
        pid = uuid.uuid4()
        links = [_make_sku_link() for _ in range(3)]
        sku = _make_orm_sku(pid, attribute_values=links)
        session = _mock_session([sku])

        handler = ListSKUsHandler(session)
        result = await handler.handle(ListSKUsQuery(product_id=pid))

        assert len(result[0].variant_attributes) == 3

    @pytest.mark.asyncio
    async def test_sku_fields_preserved(self) -> None:
        """All scalar fields are correctly mapped from ORM to read model."""
        pid = uuid.uuid4()
        sku = _make_orm_sku(
            pid,
            price=999,
            is_active=False,
            sku_code="MY-SKU-001",
        )
        session = _mock_session([sku])

        handler = ListSKUsHandler(session)
        result = await handler.handle(ListSKUsQuery(product_id=pid))

        item = result[0]
        assert item.sku_code == "MY-SKU-001"
        assert item.is_active is False
        assert item.product_id == pid
        assert item.version == 1
        assert item.created_at == _NOW
        assert item.updated_at == _NOW
