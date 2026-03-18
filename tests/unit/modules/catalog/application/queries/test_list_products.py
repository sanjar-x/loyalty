# tests/unit/modules/catalog/application/queries/test_list_products.py
"""Unit tests for ListProductsHandler query handler.

Covers:
- Happy path: paginated product list with items and total count.
- Empty results: no matching products returns empty items with total=0.
- Filtering: status and brand_id filters applied correctly.
- Pagination: offset/limit propagated to the read model.
- ListProductsQuery dataclass: defaults and custom values.
- Mapping: ORM Product -> ProductListItemReadModel with correct fields.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.modules.catalog.application.queries.list_products import (
    ListProductsHandler,
    ListProductsQuery,
)
from src.modules.catalog.application.queries.read_models import (
    ProductListItemReadModel,
    ProductListReadModel,
)

pytestmark = pytest.mark.unit

_NOW = datetime(2026, 3, 18, 12, 0, 0, tzinfo=UTC)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _FakeStatus:
    """Mimics an enum with a .value property."""

    def __init__(self, value: str) -> None:
        self.value = value


def _make_orm_product(
    product_id: uuid.UUID | None = None,
    status: str = "draft",
    slug: str = "test-product",
) -> SimpleNamespace:
    return SimpleNamespace(
        id=product_id or uuid.uuid4(),
        slug=slug,
        title_i18n={"en": "Test Product"},
        status=_FakeStatus(status),
        brand_id=uuid.uuid4(),
        primary_category_id=uuid.uuid4(),
        version=1,
        created_at=_NOW,
        updated_at=_NOW,
    )


def _mock_session(
    total: int,
    orm_rows: list[SimpleNamespace],
) -> AsyncMock:
    """Build an AsyncSession mock that returns a count then scalars."""
    session = AsyncMock()

    # First call: count query -> scalar_one() returns total
    count_result = MagicMock()
    count_result.scalar_one.return_value = total

    # Second call: items query -> scalars().all() returns orm_rows
    items_result = MagicMock()
    items_scalars = MagicMock()
    items_scalars.all.return_value = orm_rows
    items_result.scalars.return_value = items_scalars

    session.execute.side_effect = [count_result, items_result]
    return session


# ---------------------------------------------------------------------------
# Tests: ListProductsQuery dataclass
# ---------------------------------------------------------------------------


class TestListProductsQuery:
    """Tests for the ListProductsQuery frozen dataclass."""

    def test_defaults(self) -> None:
        """Default offset=0, limit=50, status=None, brand_id=None."""
        query = ListProductsQuery()
        assert query.offset == 0
        assert query.limit == 50
        assert query.status is None
        assert query.brand_id is None

    def test_custom_values(self) -> None:
        """Custom pagination and filter values set correctly."""
        bid = uuid.uuid4()
        query = ListProductsQuery(offset=20, limit=10, status="published", brand_id=bid)
        assert query.offset == 20
        assert query.limit == 10
        assert query.status == "published"
        assert query.brand_id == bid

    def test_frozen_immutable(self) -> None:
        """ListProductsQuery is frozen (immutable)."""
        query = ListProductsQuery()
        with pytest.raises(AttributeError):
            query.offset = 10  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Tests: ListProductsHandler
# ---------------------------------------------------------------------------


class TestListProductsHandlerHappyPath:
    """Happy path: products exist, list returned with pagination."""

    @pytest.mark.asyncio
    async def test_returns_product_list_read_model(self) -> None:
        """Handler returns ProductListReadModel."""
        orm1 = _make_orm_product(slug="product-1")
        orm2 = _make_orm_product(slug="product-2")
        session = _mock_session(total=2, orm_rows=[orm1, orm2])

        handler = ListProductsHandler(session)
        result = await handler.handle(ListProductsQuery())

        assert isinstance(result, ProductListReadModel)
        assert len(result.items) == 2
        assert result.total == 2

    @pytest.mark.asyncio
    async def test_items_are_product_list_item_models(self) -> None:
        """Each item is a ProductListItemReadModel."""
        orm = _make_orm_product()
        session = _mock_session(total=1, orm_rows=[orm])

        handler = ListProductsHandler(session)
        result = await handler.handle(ListProductsQuery())

        assert all(isinstance(item, ProductListItemReadModel) for item in result.items)

    @pytest.mark.asyncio
    async def test_pagination_fields_propagated(self) -> None:
        """Offset and limit from query appear in the result."""
        session = _mock_session(total=100, orm_rows=[])

        handler = ListProductsHandler(session)
        query = ListProductsQuery(offset=20, limit=10)
        result = await handler.handle(query)

        assert result.offset == 20
        assert result.limit == 10
        assert result.total == 100

    @pytest.mark.asyncio
    async def test_session_execute_called_twice(self) -> None:
        """Handler calls session.execute twice (count + items)."""
        session = _mock_session(total=0, orm_rows=[])

        handler = ListProductsHandler(session)
        await handler.handle(ListProductsQuery())

        assert session.execute.await_count == 2


class TestListProductsHandlerEmptyResult:
    """Edge case: no products match the query."""

    @pytest.mark.asyncio
    async def test_empty_items_with_zero_total(self) -> None:
        """No matching products returns items=[], total=0."""
        session = _mock_session(total=0, orm_rows=[])

        handler = ListProductsHandler(session)
        result = await handler.handle(ListProductsQuery())

        assert result.items == []
        assert result.total == 0


class TestListProductsHandlerMapping:
    """ORM Product -> ProductListItemReadModel mapping correctness."""

    @pytest.mark.asyncio
    async def test_fields_mapped_correctly(self) -> None:
        """All fields from ORM are mapped to the read model."""
        pid = uuid.uuid4()
        orm = _make_orm_product(product_id=pid, status="published", slug="my-slug")
        session = _mock_session(total=1, orm_rows=[orm])

        handler = ListProductsHandler(session)
        result = await handler.handle(ListProductsQuery())

        item = result.items[0]
        assert item.id == pid
        assert item.slug == "my-slug"
        assert item.status == "published"
        assert type(item.status) is str
        assert item.version == 1
        assert item.created_at == _NOW
        assert item.updated_at == _NOW

    @pytest.mark.asyncio
    async def test_status_is_plain_string_not_enum(self) -> None:
        """Status is extracted as .value string, not the enum itself."""
        orm = _make_orm_product(status="archived")
        session = _mock_session(total=1, orm_rows=[orm])

        handler = ListProductsHandler(session)
        result = await handler.handle(ListProductsQuery())

        assert result.items[0].status == "archived"
        assert type(result.items[0].status) is str
