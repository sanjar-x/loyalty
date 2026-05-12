"""Unit tests for :class:`RedisActivityQueryService`.

Validates the Redis → RankedEntity conversion and graceful degradation.
"""

from __future__ import annotations

import uuid
from typing import Any

import pytest

from src.modules.activity.infrastructure.redis_query_service import (
    RedisActivityQueryService,
)
from src.shared.interfaces.activity import RankedEntity

pytestmark = pytest.mark.unit


class _FakeLogger:
    def __init__(self) -> None:
        self.warnings: list[tuple[str, dict[str, Any]]] = []

    def bind(self, **_: Any) -> _FakeLogger:
        return self

    def warning(self, event: str, **kwargs: Any) -> None:
        self.warnings.append((event, kwargs))

    def info(self, *_: Any, **__: Any) -> None:  # pragma: no cover
        pass

    def error(self, *_: Any, **__: Any) -> None:  # pragma: no cover
        pass

    def critical(self, *_: Any, **__: Any) -> None:  # pragma: no cover
        pass

    def debug(self, *_: Any, **__: Any) -> None:  # pragma: no cover
        pass

    def exception(self, *_: Any, **__: Any) -> None:  # pragma: no cover
        pass


class _FakeRedis:
    def __init__(self, data: dict[str, list[tuple[bytes, float]]]) -> None:
        self._data = data

    async def zrevrange(
        self, key: str, start: int, stop: int, withscores: bool = False
    ) -> list[tuple[bytes, float]] | list[bytes]:
        entries = self._data.get(key, [])
        # Our fakes always return pre-sorted desc; slice it.
        sliced = entries[start : stop + 1]
        if withscores:
            return sliced
        return [m for m, _ in sliced]


class _RaisingRedis:
    async def zrevrange(self, *_: Any, **__: Any) -> None:
        raise ConnectionError("redis down")


@pytest.mark.asyncio
async def test_trending_weekly_returns_ranked_entities() -> None:
    pid = uuid.uuid4()
    client = _FakeRedis(
        {"trending:weekly": [(str(pid).encode(), 42.0), (b"badvalue", 1.0)]}
    )
    service = RedisActivityQueryService(client, _FakeLogger())  # ty: ignore[invalid-argument-type]

    result = await service.get_trending_products(limit=10)

    assert result == [
        RankedEntity(entity_id=str(pid), score=42.0),
        RankedEntity(entity_id="badvalue", score=1.0),
    ]


@pytest.mark.asyncio
async def test_trending_category_uses_category_key() -> None:
    cid = uuid.uuid4()
    pid = uuid.uuid4()
    client = _FakeRedis({f"trending:category:{cid}": [(str(pid).encode(), 7.0)]})
    service = RedisActivityQueryService(client, _FakeLogger())  # ty: ignore[invalid-argument-type]

    result = await service.get_trending_products(limit=5, category_id=cid)
    assert result == [RankedEntity(entity_id=str(pid), score=7.0)]


@pytest.mark.asyncio
async def test_popular_queries_returns_strings() -> None:
    client = _FakeRedis(
        {"search:popular_queries": [(b"laptop", 120.0), (b"phone", 80.0)]}
    )
    service = RedisActivityQueryService(client, _FakeLogger())  # ty: ignore[invalid-argument-type]

    result = await service.get_popular_search_queries(limit=2)
    assert [r.entity_id for r in result] == ["laptop", "phone"]
    assert [r.score for r in result] == [120.0, 80.0]


@pytest.mark.asyncio
async def test_returns_empty_on_redis_failure() -> None:
    logger = _FakeLogger()
    service = RedisActivityQueryService(_RaisingRedis(), logger)  # ty: ignore[invalid-argument-type]

    result = await service.get_zero_result_queries(limit=10)
    assert result == []
    assert logger.warnings
    assert logger.warnings[0][0] == "activity.query.redis_failure"


@pytest.mark.asyncio
async def test_limit_is_clamped() -> None:
    client = _FakeRedis({"trending:weekly": []})
    service = RedisActivityQueryService(client, _FakeLogger())  # ty: ignore[invalid-argument-type]

    # Limit outside [1, 500] must not raise.
    assert await service.get_trending_products(limit=0) == []
    assert await service.get_trending_products(limit=10_000) == []
