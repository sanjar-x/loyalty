"""Unit tests for the also-viewed orchestrator (Phase B2)."""

from __future__ import annotations

import uuid
from typing import Any

import pytest

from src.modules.catalog.application.queries.get_also_viewed import (
    GetAlsoViewedProductCardsHandler,
    GetAlsoViewedProductCardsQuery,
)
from src.modules.catalog.application.queries.get_similar_products import (
    GetSimilarProductsQuery,
    SimilarProductsResult,
)
from src.shared.exceptions import NotFoundError
from src.shared.interfaces.activity import CoViewScore

pytestmark = pytest.mark.unit


class _Row:
    def __init__(self, **kwargs: Any) -> None:
        for k, v in kwargs.items():
            setattr(self, k, v)


class _ResultFirst:
    def __init__(self, row: Any) -> None:
        self._row = row

    def first(self) -> Any:
        return self._row


class _FakeSession:
    def __init__(self, results: list[Any]) -> None:
        self._results = list(results)

    async def execute(self, *_: Any, **__: Any) -> Any:
        return self._results.pop(0)


class _FakeCoView:
    def __init__(self, scores: list[CoViewScore]) -> None:
        self._scores = scores
        self.called_with: uuid.UUID | None = None

    async def get_also_viewed(
        self, *, product_id: uuid.UUID, limit: int = 12
    ) -> list[CoViewScore]:
        self.called_with = product_id
        return self._scores


class _FakeSimilar:
    def __init__(self, ids: list[uuid.UUID]) -> None:
        self._ids = ids
        self.called = False

    async def handle(self, q: GetSimilarProductsQuery) -> SimilarProductsResult:
        self.called = True
        return SimilarProductsResult(product_ids=self._ids)


class _FakeCards:
    def __init__(self) -> None:
        self.received_ids: list[uuid.UUID] | None = None

    async def handle(self, q: Any) -> list[Any]:
        self.received_ids = q.product_ids
        return [object() for _ in q.product_ids]


class TestAlsoViewedHandler:
    async def test_404_when_slug_missing(self) -> None:
        session = _FakeSession([_ResultFirst(None)])
        h = GetAlsoViewedProductCardsHandler(
            session,  # ty: ignore[invalid-argument-type]
            _FakeCoView([]),
            _FakeSimilar([]),  # ty: ignore[invalid-argument-type]
            _FakeCards(),  # ty: ignore[invalid-argument-type]
        )
        with pytest.raises(NotFoundError):
            await h.handle(GetAlsoViewedProductCardsQuery(slug="nope"))

    async def test_uses_co_view_when_available(self) -> None:
        product_id = uuid.uuid4()
        co_ids = [uuid.uuid4() for _ in range(3)]
        session = _FakeSession([_ResultFirst(_Row(id=product_id))])
        co_view = _FakeCoView([CoViewScore(product_id=i, score=5) for i in co_ids])
        similar = _FakeSimilar([uuid.uuid4()])
        cards = _FakeCards()

        h = GetAlsoViewedProductCardsHandler(session, co_view, similar, cards)  # ty: ignore[invalid-argument-type]
        result = await h.handle(GetAlsoViewedProductCardsQuery(slug="s", limit=3))

        assert result.is_fallback is False
        assert co_view.called_with == product_id
        assert similar.called is False
        assert cards.received_ids == co_ids
        assert len(result.items) == 3

    async def test_falls_back_to_similar_when_co_view_empty(self) -> None:
        product_id = uuid.uuid4()
        fallback_ids = [uuid.uuid4(), uuid.uuid4()]
        session = _FakeSession([_ResultFirst(_Row(id=product_id))])
        co_view = _FakeCoView([])
        similar = _FakeSimilar(fallback_ids)
        cards = _FakeCards()

        h = GetAlsoViewedProductCardsHandler(session, co_view, similar, cards)  # ty: ignore[invalid-argument-type]
        result = await h.handle(GetAlsoViewedProductCardsQuery(slug="s"))

        assert result.is_fallback is True
        assert similar.called is True
        assert cards.received_ids == fallback_ids

    async def test_empty_when_both_sources_dry(self) -> None:
        product_id = uuid.uuid4()
        session = _FakeSession([_ResultFirst(_Row(id=product_id))])
        co_view = _FakeCoView([])
        similar = _FakeSimilar([])
        cards = _FakeCards()

        h = GetAlsoViewedProductCardsHandler(session, co_view, similar, cards)  # ty: ignore[invalid-argument-type]
        result = await h.handle(GetAlsoViewedProductCardsQuery(slug="s"))

        assert result.items == []
        assert result.is_fallback is True
        assert cards.received_ids is None  # cards not called

    async def test_seed_product_is_excluded_from_co_view_results(self) -> None:
        """Defensive: a stale co-view row could pair a product with itself."""
        product_id = uuid.uuid4()
        other = uuid.uuid4()
        session = _FakeSession([_ResultFirst(_Row(id=product_id))])
        co_view = _FakeCoView(
            [
                CoViewScore(product_id=product_id, score=10),  # seed itself
                CoViewScore(product_id=other, score=5),
            ]
        )
        similar = _FakeSimilar([])
        cards = _FakeCards()

        h = GetAlsoViewedProductCardsHandler(session, co_view, similar, cards)  # ty: ignore[invalid-argument-type]
        await h.handle(GetAlsoViewedProductCardsQuery(slug="s", limit=2))

        assert cards.received_ids is not None
        assert product_id not in cards.received_ids
        assert other in cards.received_ids
