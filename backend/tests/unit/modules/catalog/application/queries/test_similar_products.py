"""Unit tests for similar-product handlers (Phase B1, content-based)."""

from __future__ import annotations

import uuid
from typing import Any
from unittest.mock import AsyncMock

import pytest

from src.modules.catalog.application.queries.get_similar_product_cards import (
    GetSimilarProductCardsHandler,
    GetSimilarProductCardsQuery,
)
from src.modules.catalog.application.queries.get_similar_products import (
    GetSimilarProductsHandler,
    GetSimilarProductsQuery,
    SimilarProductsResult,
)
from src.shared.exceptions import NotFoundError

pytestmark = pytest.mark.unit


class _FakeLogger:
    def bind(self, **_: Any) -> _FakeLogger:
        return self

    def exception(self, *_: Any, **__: Any) -> None:  # pragma: no cover
        pass

    def warning(self, *_: Any, **__: Any) -> None:  # pragma: no cover
        pass


class _Row:
    def __init__(self, **kwargs: Any) -> None:
        for k, v in kwargs.items():
            setattr(self, k, v)


class _ResultFirst:
    def __init__(self, row: Any) -> None:
        self._row = row

    def first(self) -> Any:
        return self._row


class _ResultAll:
    def __init__(self, rows: list[Any]) -> None:
        self._rows = rows

    def all(self) -> list[Any]:
        return self._rows


class _FakeSession:
    """FIFO queue of pre-built Result objects returned by execute()."""

    def __init__(self, results: list[Any]) -> None:
        self._results = list(results)

    async def execute(self, *_: Any, **__: Any) -> Any:
        return self._results.pop(0)


# ---------------------------------------------------------------------------
# GetSimilarProductsHandler
# ---------------------------------------------------------------------------


class TestGetSimilarProductsHandler:
    async def test_empty_when_seed_missing(self) -> None:
        session = AsyncMock()
        session.execute = AsyncMock(return_value=_ResultFirst(None))
        handler = GetSimilarProductsHandler(session, _FakeLogger())
        result = await handler.handle(GetSimilarProductsQuery(product_id=uuid.uuid4()))
        assert result.product_ids == []

    async def test_returns_ids_from_query(self) -> None:
        seed = _Row(primary_category_id=uuid.uuid4(), brand_id=uuid.uuid4())
        ids = [uuid.uuid4() for _ in range(3)]
        session = _FakeSession(
            results=[_ResultFirst(seed), _ResultAll([_Row(id=i) for i in ids])]
        )
        handler = GetSimilarProductsHandler(session, _FakeLogger())
        result = await handler.handle(
            GetSimilarProductsQuery(product_id=uuid.uuid4(), limit=10)
        )
        assert result.product_ids == ids

    async def test_empty_when_seed_has_no_category(self) -> None:
        seed = _Row(primary_category_id=None, brand_id=uuid.uuid4())
        session = _FakeSession(results=[_ResultFirst(seed)])
        handler = GetSimilarProductsHandler(session, _FakeLogger())
        result = await handler.handle(GetSimilarProductsQuery(product_id=uuid.uuid4()))
        assert result.product_ids == []

    async def test_limit_clamped_to_50(self) -> None:
        seed = _Row(primary_category_id=uuid.uuid4(), brand_id=uuid.uuid4())
        session = _FakeSession(results=[_ResultFirst(seed), _ResultAll([])])
        handler = GetSimilarProductsHandler(session, _FakeLogger())
        # limit=999 should not raise; just return empty from our fake.
        result = await handler.handle(
            GetSimilarProductsQuery(product_id=uuid.uuid4(), limit=999)
        )
        assert result.product_ids == []


# ---------------------------------------------------------------------------
# GetSimilarProductCardsHandler — orchestrator
# ---------------------------------------------------------------------------


class _FakeSimilarHandler:
    def __init__(self, ids: list[uuid.UUID]) -> None:
        self._ids = ids
        self.called_with: uuid.UUID | None = None

    async def handle(self, q: GetSimilarProductsQuery) -> SimilarProductsResult:
        self.called_with = q.product_id
        return SimilarProductsResult(product_ids=self._ids)


class _FakeCardsHandler:
    def __init__(self) -> None:
        self.received_ids: list[uuid.UUID] | None = None

    async def handle(self, q: Any) -> list[Any]:
        self.received_ids = q.product_ids
        return [object() for _ in q.product_ids]


class TestSimilarProductCardsHandler:
    async def test_404_when_slug_missing(self) -> None:
        session = _FakeSession(results=[_ResultFirst(None)])
        h = GetSimilarProductCardsHandler(
            session, _FakeSimilarHandler([]), _FakeCardsHandler()
        )
        with pytest.raises(NotFoundError):
            await h.handle(GetSimilarProductCardsQuery(slug="nope"))

    async def test_empty_short_circuits_cards_fetch(self) -> None:
        product_id = uuid.uuid4()
        session = _FakeSession(results=[_ResultFirst(_Row(id=product_id))])
        similar = _FakeSimilarHandler([])
        cards = _FakeCardsHandler()
        h = GetSimilarProductCardsHandler(session, similar, cards)
        result = await h.handle(GetSimilarProductCardsQuery(slug="s"))
        assert result.items == []
        assert cards.received_ids is None

    async def test_happy_path_preserves_order(self) -> None:
        product_id = uuid.uuid4()
        ranked = [uuid.uuid4() for _ in range(4)]
        session = _FakeSession(results=[_ResultFirst(_Row(id=product_id))])
        similar = _FakeSimilarHandler(ranked)
        cards = _FakeCardsHandler()
        h = GetSimilarProductCardsHandler(session, similar, cards)
        result = await h.handle(GetSimilarProductCardsQuery(slug="s", limit=5))
        assert similar.called_with == product_id
        assert cards.received_ids == ranked
        assert len(result.items) == 4
