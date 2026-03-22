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


def _mock_session(rows: list = []) -> AsyncMock:  # noqa: B006
    """Build an AsyncSession mock returning count then data rows.

    The handler calls session.execute twice: first for COUNT, then for data.
    """
    from unittest.mock import MagicMock

    session = AsyncMock()

    # First call: COUNT query -> scalar_one() returns len(rows)
    count_result_mock = MagicMock()
    count_result_mock.scalar_one.return_value = len(rows)

    # Second call: data query -> all() returns rows (tuples of (pav, attr))
    data_result_mock = MagicMock()
    data_result_mock.all.return_value = rows

    session.execute.side_effect = [count_result_mock, data_result_mock]
    return session


class TestListProductAttributesHandler:
    """Tests for ListProductAttributesHandler."""

    @pytest.mark.asyncio
    async def test_returns_empty_list_with_zero_total(self) -> None:
        """Handler returns (empty list, 0) when no attributes exist."""
        session = _mock_session([])
        handler = ListProductAttributesHandler(session)
        query = ListProductAttributesQuery(product_id=uuid.uuid4())

        items, total = await handler.handle(query)

        assert isinstance(items, list)
        assert items == []
        assert total == 0

    @pytest.mark.asyncio
    async def test_session_execute_called_twice(self) -> None:
        """Handler calls session.execute twice (count + data)."""
        session = _mock_session([])
        handler = ListProductAttributesHandler(session)
        query = ListProductAttributesQuery(product_id=uuid.uuid4())

        await handler.handle(query)

        assert session.execute.await_count == 2

    @pytest.mark.asyncio
    async def test_handler_stores_session(self) -> None:
        """Handler stores the session."""
        session = AsyncMock()
        handler = ListProductAttributesHandler(session)
        assert handler._session is session
