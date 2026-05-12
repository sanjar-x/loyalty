"""Unit tests for :class:`RedisActivityTracker`.

We use a stub Redis client to verify the pipeline interactions without
needing a real Redis instance.  The key assertions are:

1. Events reach the ``activity:event_queue`` via ``LPUSH``.
2. Trending sorted sets are incremented with ``ZINCRBY``.
3. All methods are fire-and-forget — they never raise.
"""

from __future__ import annotations

import json
import uuid
from typing import Any

import pytest

from src.modules.activity.infrastructure.redis_tracker import (
    ACTIVITY_QUEUE_KEY,
    TRENDING_WEEKLY_KEY,
    RedisActivityTracker,
    trending_daily_key,
)

pytestmark = pytest.mark.unit


class _FakePipeline:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[Any, ...]]] = []

    def zincrby(self, *args: Any) -> None:
        self.calls.append(("zincrby", args))

    def expire(self, *args: Any) -> None:
        self.calls.append(("expire", args))

    def lpush(self, *args: Any) -> None:
        self.calls.append(("lpush", args))

    def ltrim(self, *args: Any) -> None:
        self.calls.append(("ltrim", args))

    async def execute(self) -> list[Any]:
        return [1] * len(self.calls)


class _FakeRedis:
    def __init__(self) -> None:
        self.last_pipeline: _FakePipeline | None = None

    def pipeline(self, transaction: bool = False) -> _FakePipeline:
        self.last_pipeline = _FakePipeline()
        return self.last_pipeline


class _NoopLogger:
    def bind(self, **kwargs: Any) -> _NoopLogger:
        return self

    def info(self, *args: Any, **kwargs: Any) -> None:  # pragma: no cover
        pass

    def warning(self, *args: Any, **kwargs: Any) -> None:  # pragma: no cover
        pass

    def error(self, *args: Any, **kwargs: Any) -> None:  # pragma: no cover
        pass

    def critical(self, *args: Any, **kwargs: Any) -> None:  # pragma: no cover
        pass

    def debug(self, *args: Any, **kwargs: Any) -> None:  # pragma: no cover
        pass

    def exception(self, *args: Any, **kwargs: Any) -> None:  # pragma: no cover
        pass


def _lpush_payload(pipe: _FakePipeline) -> dict[str, Any]:
    for name, args in pipe.calls:
        if name == "lpush":
            key, body = args
            assert key == ACTIVITY_QUEUE_KEY
            return json.loads(body)
    raise AssertionError("no LPUSH call recorded")


async def test_track_product_view_enqueues_event_and_bumps_trending() -> None:
    redis = _FakeRedis()
    tracker = RedisActivityTracker(redis, _NoopLogger())  # ty: ignore[invalid-argument-type]

    product_id = uuid.uuid4()
    category_id = uuid.uuid4()
    actor_id = uuid.uuid4()

    await tracker.track_product_view(
        product_id=product_id,
        category_id=category_id,
        actor_id=actor_id,
        session_id="sess-1",
    )

    pipe = redis.last_pipeline
    assert pipe is not None

    ops = [call[0] for call in pipe.calls]
    assert "zincrby" in ops
    assert "lpush" in ops
    assert "ltrim" in ops

    # Daily + weekly + category trending keys all touched.
    zincrby_keys = {args[0] for name, args in pipe.calls if name == "zincrby"}
    assert trending_daily_key() in zincrby_keys
    assert TRENDING_WEEKLY_KEY in zincrby_keys

    body = _lpush_payload(pipe)
    assert body["event_type"] == "product_viewed"
    assert body["product_id"] == str(product_id)
    assert body["actor_id"] == str(actor_id)
    assert body["session_id"] == "sess-1"
    assert body["payload"]["product_id"] == str(product_id)


async def test_track_search_ignores_empty_query() -> None:
    redis = _FakeRedis()
    tracker = RedisActivityTracker(redis, _NoopLogger())  # ty: ignore[invalid-argument-type]

    await tracker.track_search(
        query="   ",
        result_count=0,
        actor_id=None,
        session_id=None,
    )

    assert redis.last_pipeline is None  # no call made


async def test_track_search_zero_results_increments_zero_bucket() -> None:
    redis = _FakeRedis()
    tracker = RedisActivityTracker(redis, _NoopLogger())  # ty: ignore[invalid-argument-type]

    await tracker.track_search(
        query="  iPhone 99  ",
        result_count=0,
        actor_id=None,
        session_id="anon-1",
    )

    pipe = redis.last_pipeline
    assert pipe is not None
    zincrby_keys = [args[0] for name, args in pipe.calls if name == "zincrby"]
    assert "search:popular_queries" in zincrby_keys
    assert "search:zero_results" in zincrby_keys

    body = _lpush_payload(pipe)
    assert body["event_type"] == "search_performed"
    # Query is normalised to lowercase + stripped.
    assert body["search_query"] == "iphone 99"


async def test_track_product_list_view_does_not_raise_on_redis_error() -> None:
    class BrokenRedis:
        def pipeline(self, transaction: bool = False) -> Any:
            raise RuntimeError("boom")

    tracker = RedisActivityTracker(BrokenRedis(), _NoopLogger())  # ty: ignore[invalid-argument-type]

    # Must NOT raise — analytics is best-effort.
    await tracker.track_product_list_view(
        category_id=None,
        result_count=5,
        actor_id=None,
        session_id=None,
    )
