# tests/unit/modules/catalog/application/queries/test_list_product_attributes.py
"""Unit tests for ListProductAttributesHandler query handler.

Covers:
- Happy path: handler returns empty list (stub until MT-16 ORM model).
- ListProductAttributesQuery dataclass: product_id required, frozen.
- Session is accepted but not queried (until MT-16).
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

import pytest

from src.modules.catalog.application.queries.list_product_attributes import (
    ListProductAttributesHandler,
    ListProductAttributesQuery,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Tests: ListProductAttributesQuery
# ---------------------------------------------------------------------------


class TestListProductAttributesQuery:
    """Tests for the ListProductAttributesQuery frozen dataclass."""

    def test_product_id_required(self) -> None:
        """product_id is a required field."""
        pid = uuid.uuid4()
        query = ListProductAttributesQuery(product_id=pid)
        assert query.product_id == pid

    def test_frozen_immutable(self) -> None:
        """ListProductAttributesQuery is frozen (immutable)."""
        query = ListProductAttributesQuery(product_id=uuid.uuid4())
        with pytest.raises(AttributeError):
            query.product_id = uuid.uuid4()  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Tests: ListProductAttributesHandler
# ---------------------------------------------------------------------------


class TestListProductAttributesHandlerStub:
    """Handler is a stub until MT-16: always returns empty list."""

    @pytest.mark.asyncio
    async def test_returns_empty_list(self) -> None:
        """Handler returns an empty list (stub behavior)."""
        session = AsyncMock()
        handler = ListProductAttributesHandler(session)
        query = ListProductAttributesQuery(product_id=uuid.uuid4())

        result = await handler.handle(query)

        assert isinstance(result, list)
        assert result == []

    @pytest.mark.asyncio
    async def test_return_type_is_list_of_product_attribute_value_read_model(self) -> None:
        """Return type annotation is list[ProductAttributeValueReadModel]."""
        session = AsyncMock()
        handler = ListProductAttributesHandler(session)
        query = ListProductAttributesQuery(product_id=uuid.uuid4())

        result = await handler.handle(query)

        # Empty list conforms to list[ProductAttributeValueReadModel]
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_session_not_queried(self) -> None:
        """Session.execute is NOT called (stub -- no ORM model yet)."""
        session = AsyncMock()
        handler = ListProductAttributesHandler(session)
        query = ListProductAttributesQuery(product_id=uuid.uuid4())

        await handler.handle(query)

        session.execute.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_accepts_any_product_id(self) -> None:
        """Handler accepts any UUID without error."""
        session = AsyncMock()
        handler = ListProductAttributesHandler(session)

        for _ in range(3):
            result = await handler.handle(ListProductAttributesQuery(product_id=uuid.uuid4()))
            assert result == []

    @pytest.mark.asyncio
    async def test_handler_stores_session(self) -> None:
        """Handler stores the session for future use (MT-16)."""
        session = AsyncMock()
        handler = ListProductAttributesHandler(session)
        assert handler._session is session
