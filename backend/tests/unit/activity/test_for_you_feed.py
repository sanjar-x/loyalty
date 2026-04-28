"""Unit tests for :class:`ForYouFeedHandler` and its cursor helper.

These tests use pure in-memory fakes for every collaborator — no DB, no
Redis, no network.  The goal is to verify the ranking/pagination logic,
cold→warm branching, and cursor round-trip.

We stub the ``session`` and cards handler because the handler's SQL paths
(category pool fetch + cold-start popularity fallback) are covered by
integration tests.  Here we focus on orchestration.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from typing import Any
from unittest.mock import AsyncMock

import pytest

from src.modules.catalog.application.queries.get_for_you_feed import (
    STRATEGY_VERSION,
    ForYouCursor,
    ForYouFeedHandler,
    ForYouFeedQuery,
    _candidate_cache_key,
)
from src.shared.interfaces.activity import CategoryAffinity, CoViewScore, RankedEntity

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class _FakeLogger:
    def bind(self, **_: Any) -> _FakeLogger:
        return self

    def warning(self, *_: Any, **__: Any) -> None:
        return None

    def info(self, *_: Any, **__: Any) -> None:
        return None


class _FakeRedis:
    def __init__(self) -> None:
        self.store: dict[str, str] = {}

    async def get(self, key: str) -> str | None:
        return self.store.get(key)

    async def set(self, key: str, value: str, ex: int | None = None) -> None:
        self.store[key] = value


class _FakeHistoryReader:
    def __init__(
        self,
        affinities: list[CategoryAffinity] | None = None,
        viewed: list[uuid.UUID] | None = None,
        event_count: int = 0,
    ) -> None:
        self._affinities = affinities or []
        self._viewed = viewed or []
        self._count = event_count

    async def get_category_affinities(self, **_: Any) -> list[CategoryAffinity]:
        return self._affinities

    async def get_recently_viewed_product_ids(self, **_: Any) -> list[uuid.UUID]:
        return self._viewed

    async def get_activity_event_count(self, **_: Any) -> int:
        return self._count


class _FakeTrending:
    def __init__(self, entries: list[RankedEntity]) -> None:
        self._entries = entries

    async def get_trending_products(self, **_: Any) -> list[RankedEntity]:
        return self._entries

    async def get_popular_search_queries(self, **_: Any) -> list[RankedEntity]:
        return []

    async def get_zero_result_queries(self, **_: Any) -> list[RankedEntity]:
        return []


class _FakeCoViewReader:
    def __init__(
        self, matrix: dict[uuid.UUID, list[CoViewScore]] | None = None
    ) -> None:
        self._matrix = matrix or {}

    async def get_also_viewed(
        self, *, product_id: uuid.UUID, limit: int = 12
    ) -> list[CoViewScore]:
        return list(self._matrix.get(product_id, []))[:limit]


@dataclass
class _CardStub:
    product_id: uuid.UUID


class _FakeCardsHandler:
    async def handle(self, query: Any) -> list[_CardStub]:
        return [_CardStub(product_id=pid) for pid in query.product_ids]


def _mk_ranked(ids: list[uuid.UUID]) -> list[RankedEntity]:
    return [
        RankedEntity(entity_id=str(pid), score=100.0 - i) for i, pid in enumerate(ids)
    ]


def _make_handler(
    *,
    trending_ids: list[uuid.UUID],
    history: _FakeHistoryReader | None = None,
    redis_store: _FakeRedis | None = None,
    co_view: _FakeCoViewReader | None = None,
) -> tuple[ForYouFeedHandler, _FakeRedis]:
    redis_fake = redis_store or _FakeRedis()
    handler = ForYouFeedHandler(
        session=AsyncMock(),  # unused for cold + cached paths in these tests
        redis_client=redis_fake,  # ty:ignore[invalid-argument-type]
        history_reader=history or _FakeHistoryReader(),
        trending_service=_FakeTrending(_mk_ranked(trending_ids)),
        co_view_reader=co_view or _FakeCoViewReader(),
        cards_handler=_FakeCardsHandler(),  # ty:ignore[invalid-argument-type]
        logger=_FakeLogger(),  # ty:ignore[invalid-argument-type]
    )
    return handler, redis_fake


# ---------------------------------------------------------------------------
# Cursor
# ---------------------------------------------------------------------------


class TestCursor:
    def test_round_trip(self) -> None:
        token = ForYouCursor(strategy_version="v1", seed_id="c:abc", offset=40).encode()
        decoded = ForYouCursor.decode(token)
        assert decoded is not None
        assert decoded.strategy_version == "v1"
        assert decoded.seed_id == "c:abc"
        assert decoded.offset == 40

    def test_decode_rejects_garbage(self) -> None:
        assert ForYouCursor.decode("not-base64!") is None
        assert ForYouCursor.decode("") is None


# ---------------------------------------------------------------------------
# Handler — cold path
# ---------------------------------------------------------------------------


class TestColdPath:
    @pytest.mark.asyncio
    async def test_anonymous_returns_trending_ordered(self) -> None:
        trending_ids = [uuid.uuid4() for _ in range(5)]
        handler, redis_fake = _make_handler(trending_ids=trending_ids)

        # Stub the session: cold fallback's supplementary popularity query
        # is only hit when trending list is shorter than MAX_CANDIDATES.
        # Simulate "no extras" by returning an empty scalar iterator.
        async def _exec(_stmt: Any) -> Any:
            class _R:
                def scalars(self) -> list[uuid.UUID]:
                    return []

            return _R()

        handler._session.execute = _exec  # ty: ignore[invalid-assignment]

        result = await handler.handle(ForYouFeedQuery(user_id=None, limit=3))

        assert result.strategy_version == STRATEGY_VERSION
        assert result.is_personalized is False
        assert [c.id for c in result.items] == trending_ids[:3]
        assert result.next_cursor is not None

        # Candidate list cached for pagination.
        decoded = ForYouCursor.decode(result.next_cursor)
        assert decoded is not None
        cached = redis_fake.store[_candidate_cache_key(decoded.seed_id)]
        assert json.loads(cached) == [str(pid) for pid in trending_ids]
        assert decoded.seed_id.startswith("c:")

    @pytest.mark.asyncio
    async def test_warm_below_threshold_falls_back_to_cold(self) -> None:
        trending_ids = [uuid.uuid4() for _ in range(3)]
        history = _FakeHistoryReader(event_count=2)  # below WARM_THRESHOLD=5
        handler, _ = _make_handler(trending_ids=trending_ids, history=history)

        async def _exec(_stmt: Any) -> Any:
            class _R:
                def scalars(self) -> list[uuid.UUID]:
                    return []

            return _R()

        handler._session.execute = _exec  # ty: ignore[invalid-assignment]

        result = await handler.handle(ForYouFeedQuery(user_id=uuid.uuid4(), limit=10))
        assert result.is_personalized is False
        assert [c.id for c in result.items] == trending_ids


# ---------------------------------------------------------------------------
# Handler — warm path
# ---------------------------------------------------------------------------


class TestWarmPath:
    @pytest.mark.asyncio
    async def test_warm_interleaves_categories_and_dedupes_viewed(self) -> None:
        cat_a, cat_b = uuid.uuid4(), uuid.uuid4()
        # Two products per category.
        a1, a2 = uuid.uuid4(), uuid.uuid4()
        b1, b2 = uuid.uuid4(), uuid.uuid4()
        viewed_already = a1  # must be deduped out

        history = _FakeHistoryReader(
            affinities=[
                CategoryAffinity(category_id=cat_a, weight=3.0),
                CategoryAffinity(category_id=cat_b, weight=1.0),
            ],
            viewed=[viewed_already],
            event_count=20,
        )

        # Mock the per-category SQL fetch to inject deterministic pools.
        pools = {cat_a: [a1, a2], cat_b: [b1, b2]}

        async def _fetch(self, category_ids):
            return {cid: pools[cid] for cid in category_ids}

        handler, _ = _make_handler(
            trending_ids=[],  # no trending tail for this test
            history=history,
        )
        handler._fetch_products_by_category = _fetch.__get__(handler, ForYouFeedHandler)  # ty: ignore[invalid-assignment]

        result = await handler.handle(ForYouFeedQuery(user_id=uuid.uuid4(), limit=5))
        ids_out = [c.id for c in result.items]

        assert result.is_personalized is True
        assert viewed_already not in ids_out
        # Category A has 3x the weight of B, so the first emitted item
        # should come from A (a2, because a1 is filtered).
        assert ids_out[0] == a2
        # b1 and b2 should also appear (exploration + diversity).
        assert b1 in ids_out
        assert b2 in ids_out

    @pytest.mark.asyncio
    async def test_warm_boosts_co_viewed_products(self) -> None:
        """v2: co-view neighbours of recently viewed items lead the feed."""
        cat_a = uuid.uuid4()
        a1, a2 = uuid.uuid4(), uuid.uuid4()
        recent = uuid.uuid4()  # recently viewed (will be deduped)
        co_hot = uuid.uuid4()  # frequently co-viewed with `recent`
        co_warm = uuid.uuid4()

        history = _FakeHistoryReader(
            affinities=[CategoryAffinity(category_id=cat_a, weight=1.0)],
            viewed=[recent],
            event_count=20,
        )
        co_view = _FakeCoViewReader(
            matrix={
                recent: [
                    CoViewScore(product_id=co_hot, score=42),
                    CoViewScore(product_id=co_warm, score=7),
                ]
            }
        )
        pools = {cat_a: [a1, a2]}

        async def _fetch(self, category_ids):
            return {cid: pools[cid] for cid in category_ids}

        handler, _ = _make_handler(trending_ids=[], history=history, co_view=co_view)
        handler._fetch_products_by_category = _fetch.__get__(handler, ForYouFeedHandler)  # ty: ignore[invalid-assignment]

        result = await handler.handle(ForYouFeedQuery(user_id=uuid.uuid4(), limit=5))
        ids_out = [c.id for c in result.items]

        assert result.strategy_version == "v2"
        assert result.is_personalized is True
        # Co-view head precedes category-affinity items.
        assert ids_out[0] == co_hot
        assert ids_out[1] == co_warm
        # Seed (recently viewed) never re-surfaces.
        assert recent not in ids_out
        # Category products still appear below the boost.
        assert a1 in ids_out and a2 in ids_out

    @pytest.mark.asyncio
    async def test_warm_without_co_view_matrix_falls_back_to_v1_ordering(
        self,
    ) -> None:
        """Empty co-view matrix must not break the warm path."""
        cat_a = uuid.uuid4()
        a1, a2 = uuid.uuid4(), uuid.uuid4()
        history = _FakeHistoryReader(
            affinities=[CategoryAffinity(category_id=cat_a, weight=1.0)],
            viewed=[uuid.uuid4()],
            event_count=20,
        )
        pools = {cat_a: [a1, a2]}

        async def _fetch(self, category_ids):
            return {cid: pools[cid] for cid in category_ids}

        handler, _ = _make_handler(trending_ids=[], history=history)
        handler._fetch_products_by_category = _fetch.__get__(handler, ForYouFeedHandler)  # ty: ignore[invalid-assignment]

        result = await handler.handle(ForYouFeedQuery(user_id=uuid.uuid4(), limit=5))
        ids_out = [c.id for c in result.items]
        assert ids_out == [a1, a2]


# ---------------------------------------------------------------------------
# Pagination (cache hit path)
# ---------------------------------------------------------------------------


class TestPagination:
    @pytest.mark.asyncio
    async def test_cursor_pagination_uses_cached_list(self) -> None:
        trending_ids = [uuid.uuid4() for _ in range(8)]
        handler, redis_fake = _make_handler(trending_ids=trending_ids)

        async def _exec(_stmt: Any) -> Any:
            class _R:
                def scalars(self) -> list[uuid.UUID]:
                    return []

            return _R()

        handler._session.execute = _exec  # ty: ignore[invalid-assignment]

        first = await handler.handle(ForYouFeedQuery(user_id=None, limit=3))
        assert first.next_cursor is not None

        # Same handler instance replays — candidate list MUST come from cache.
        second = await handler.handle(
            ForYouFeedQuery(user_id=None, limit=3, cursor=first.next_cursor)
        )

        all_ids = [c.id for c in first.items] + [c.id for c in second.items]
        assert all_ids == trending_ids[:6]

        third = await handler.handle(
            ForYouFeedQuery(user_id=None, limit=3, cursor=second.next_cursor)
        )
        # 8 total, windows 3+3+2 → third cursor is final.
        assert [c.id for c in third.items] == trending_ids[6:]
        assert third.next_cursor is None
        # Redis should still hold the seed list.
        assert len(redis_fake.store) == 1

    @pytest.mark.asyncio
    async def test_stale_strategy_version_resets(self) -> None:
        trending_ids = [uuid.uuid4() for _ in range(4)]
        handler, _ = _make_handler(trending_ids=trending_ids)

        async def _exec(_stmt: Any) -> Any:
            class _R:
                def scalars(self) -> list[uuid.UUID]:
                    return []

            return _R()

        handler._session.execute = _exec  # ty: ignore[invalid-assignment]

        stale_cursor = ForYouCursor(
            strategy_version="v999", seed_id="c:old", offset=2
        ).encode()
        result = await handler.handle(
            ForYouFeedQuery(user_id=None, limit=2, cursor=stale_cursor)
        )
        # Should rebuild from scratch, returning the first 2 trending items.
        assert [c.id for c in result.items] == trending_ids[:2]


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    @pytest.mark.asyncio
    async def test_limit_is_clamped_to_1_50(self) -> None:
        trending_ids = [uuid.uuid4() for _ in range(60)]
        handler, _ = _make_handler(trending_ids=trending_ids)

        async def _exec(_stmt: Any) -> Any:
            class _R:
                def scalars(self) -> list[uuid.UUID]:
                    return []

            return _R()

        handler._session.execute = _exec  # ty: ignore[invalid-assignment]

        # limit=0 → clamped to 1
        r_zero = await handler.handle(ForYouFeedQuery(user_id=None, limit=0))
        assert len(r_zero.items) == 1

        # limit=9999 → clamped to 50
        r_big = await handler.handle(ForYouFeedQuery(user_id=None, limit=9999))
        assert len(r_big.items) == 50

    @pytest.mark.asyncio
    async def test_negative_cursor_offset_is_clamped_to_zero(self) -> None:
        """A crafted cursor with a negative offset must not wrap the slice.

        Python list slicing with a negative start returns the tail — leaking
        stale items and producing an infinite ``next_cursor`` loop because
        ``new_offset < len(candidate_ids)`` would stay true forever.
        """
        trending_ids = [uuid.uuid4() for _ in range(5)]
        handler, _redis_fake = _make_handler(trending_ids=trending_ids)

        async def _exec(_stmt: Any) -> Any:
            class _R:
                def scalars(self) -> list[uuid.UUID]:
                    return []

            return _R()

        handler._session.execute = _exec  # ty: ignore[invalid-assignment]

        # Seed the cache and grab a legitimate seed_id.
        first = await handler.handle(ForYouFeedQuery(user_id=None, limit=2))
        seed_id = ForYouCursor.decode(first.next_cursor or "").seed_id  # ty: ignore[unresolved-attribute]

        malicious_cursor = ForYouCursor(
            strategy_version=STRATEGY_VERSION,
            seed_id=seed_id,
            offset=-3,
        ).encode()
        result = await handler.handle(
            ForYouFeedQuery(user_id=None, limit=2, cursor=malicious_cursor)
        )
        # Starts from the head, not the tail.
        assert [c.id for c in result.items] == trending_ids[:2]

    @pytest.mark.asyncio
    async def test_cursor_with_evicted_cache_restarts_from_zero(self) -> None:
        """If Redis drops the candidate list between page 1 and 2, we
        must rebuild and paginate from offset 0 — not skip to the old
        offset against a different list."""
        trending_ids = [uuid.uuid4() for _ in range(4)]
        handler, redis_fake = _make_handler(trending_ids=trending_ids)

        async def _exec(_stmt: Any) -> Any:
            class _R:
                def scalars(self) -> list[uuid.UUID]:
                    return []

            return _R()

        handler._session.execute = _exec  # ty: ignore[invalid-assignment]

        first = await handler.handle(ForYouFeedQuery(user_id=None, limit=2))
        assert first.next_cursor is not None

        # Simulate TTL eviction.
        redis_fake.store.clear()

        second = await handler.handle(
            ForYouFeedQuery(user_id=None, limit=2, cursor=first.next_cursor)
        )
        # Rebuilt from fresh trending, returns head — not a 2-offset window.
        assert [c.id for c in second.items] == trending_ids[:2]

    @pytest.mark.asyncio
    async def test_huge_cursor_offset_returns_empty_without_next(self) -> None:
        trending_ids = [uuid.uuid4() for _ in range(3)]
        handler, _ = _make_handler(trending_ids=trending_ids)

        async def _exec(_stmt: Any) -> Any:
            class _R:
                def scalars(self) -> list[uuid.UUID]:
                    return []

            return _R()

        handler._session.execute = _exec  # ty: ignore[invalid-assignment]

        first = await handler.handle(ForYouFeedQuery(user_id=None, limit=2))
        seed_id = ForYouCursor.decode(first.next_cursor or "").seed_id  # ty: ignore[unresolved-attribute]

        cursor = ForYouCursor(
            strategy_version=STRATEGY_VERSION,
            seed_id=seed_id,
            offset=9999,
        ).encode()
        result = await handler.handle(
            ForYouFeedQuery(user_id=None, limit=2, cursor=cursor)
        )
        assert result.items == []
        assert result.next_cursor is None

    def test_decode_rejects_missing_fields_and_bad_types(self) -> None:
        # Valid base64 JSON but missing required fields.
        import base64 as _b64

        bad_payload = _b64.urlsafe_b64encode(b'{"v": "v1"}').rstrip(b"=").decode()
        assert ForYouCursor.decode(bad_payload) is None

        # offset is not coercible to int.
        bad2 = (
            _b64.urlsafe_b64encode(b'{"v":"v1","s":"x","o":"abc"}')
            .rstrip(b"=")
            .decode()
        )
        assert ForYouCursor.decode(bad2) is None
