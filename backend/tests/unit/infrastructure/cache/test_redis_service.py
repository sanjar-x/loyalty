"""Unit tests for the extended ``RedisService`` (ICacheService impl).

Covers the batch and atomic operations added on top of the original
set/get/delete protocol: ``get_many``, ``set_many``, ``exists``,
``expire``, ``increment`` — including the graceful-degradation contract
(all methods must swallow ``RedisError`` and return a neutral value).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from redis.exceptions import RedisError

from src.infrastructure.cache.redis import RedisService


@pytest.fixture
def client() -> MagicMock:
    mock = MagicMock()
    mock.set = AsyncMock(return_value=True)
    mock.get = AsyncMock(return_value=None)
    mock.delete = AsyncMock(return_value=0)
    mock.mget = AsyncMock(return_value=[])
    mock.mset = AsyncMock(return_value=True)
    mock.exists = AsyncMock(return_value=0)
    mock.expire = AsyncMock(return_value=True)
    mock.incrby = AsyncMock(return_value=1)
    mock.ttl = AsyncMock(return_value=-1)
    return mock


@pytest.fixture
def service(client: MagicMock) -> RedisService:
    return RedisService(client)


# ---------------------------------------------------------------------------
# get_many
# ---------------------------------------------------------------------------


class TestGetMany:
    async def test_empty_input_skips_redis(
        self, service: RedisService, client: MagicMock
    ) -> None:
        assert await service.get_many([]) == {}
        client.mget.assert_not_called()

    async def test_decodes_bytes_and_preserves_missing(
        self, service: RedisService, client: MagicMock
    ) -> None:
        client.mget.return_value = [b"hello", None, b"world"]
        result = await service.get_many(["a", "b", "c"])
        assert result == {"a": "hello", "b": None, "c": "world"}
        client.mget.assert_awaited_once_with(["a", "b", "c"])

    async def test_redis_error_maps_every_key_to_none(
        self, service: RedisService, client: MagicMock
    ) -> None:
        client.mget.side_effect = RedisError("boom")
        result = await service.get_many(["a", "b"])
        assert result == {"a": None, "b": None}


# ---------------------------------------------------------------------------
# set_many
# ---------------------------------------------------------------------------


class TestSetMany:
    async def test_empty_input_skips_redis(
        self, service: RedisService, client: MagicMock
    ) -> None:
        await service.set_many({})
        client.mset.assert_not_called()
        client.pipeline.assert_not_called()

    async def test_without_ttl_uses_mset(
        self, service: RedisService, client: MagicMock
    ) -> None:
        await service.set_many({"a": "1", "b": "2"})
        client.mset.assert_awaited_once_with({"a": "1", "b": "2"})
        client.pipeline.assert_not_called()

    async def test_with_ttl_pipelines_set_ex(
        self, service: RedisService, client: MagicMock
    ) -> None:
        pipe = MagicMock()
        pipe.set = MagicMock()
        pipe.execute = AsyncMock(return_value=[True, True])
        client.pipeline = MagicMock(return_value=pipe)

        await service.set_many({"a": "1", "b": "2"}, ttl=60)

        client.pipeline.assert_called_once_with(transaction=False)
        assert pipe.set.call_count == 2
        pipe.set.assert_any_call("a", "1", ex=60)
        pipe.set.assert_any_call("b", "2", ex=60)
        pipe.execute.assert_awaited_once()

    async def test_redis_error_is_swallowed(
        self, service: RedisService, client: MagicMock
    ) -> None:
        client.mset.side_effect = RedisError("down")
        await service.set_many({"a": "1"})  # must not raise


# ---------------------------------------------------------------------------
# exists / expire
# ---------------------------------------------------------------------------


class TestExists:
    async def test_returns_true_when_redis_reports_one(
        self, service: RedisService, client: MagicMock
    ) -> None:
        client.exists.return_value = 1
        assert await service.exists("k") is True

    async def test_returns_false_when_missing(
        self, service: RedisService, client: MagicMock
    ) -> None:
        client.exists.return_value = 0
        assert await service.exists("k") is False

    async def test_returns_false_on_error(
        self, service: RedisService, client: MagicMock
    ) -> None:
        client.exists.side_effect = RedisError("boom")
        assert await service.exists("k") is False


class TestExpire:
    async def test_non_positive_ttl_returns_false(
        self, service: RedisService, client: MagicMock
    ) -> None:
        assert await service.expire("k", 0) is False
        assert await service.expire("k", -5) is False
        client.expire.assert_not_called()

    async def test_applies_ttl(
        self, service: RedisService, client: MagicMock
    ) -> None:
        client.expire.return_value = 1
        assert await service.expire("k", 30) is True
        client.expire.assert_awaited_once_with("k", 30)

    async def test_returns_false_on_error(
        self, service: RedisService, client: MagicMock
    ) -> None:
        client.expire.side_effect = RedisError("boom")
        assert await service.expire("k", 30) is False


# ---------------------------------------------------------------------------
# increment
# ---------------------------------------------------------------------------


class TestIncrement:
    async def test_returns_new_counter_value(
        self, service: RedisService, client: MagicMock
    ) -> None:
        client.incrby.return_value = 42
        assert await service.increment("counter", 5) == 42
        client.incrby.assert_awaited_once_with("counter", 5)

    async def test_applies_ttl_only_when_key_has_none(
        self, service: RedisService, client: MagicMock
    ) -> None:
        client.incrby.return_value = 1
        client.ttl.return_value = -1  # no TTL set
        await service.increment("counter", 1, ttl=120)
        client.expire.assert_awaited_once_with("counter", 120)

    async def test_does_not_refresh_existing_ttl(
        self, service: RedisService, client: MagicMock
    ) -> None:
        client.incrby.return_value = 2
        client.ttl.return_value = 30  # already has TTL
        await service.increment("counter", 1, ttl=120)
        client.expire.assert_not_called()

    async def test_no_ttl_when_not_requested(
        self, service: RedisService, client: MagicMock
    ) -> None:
        client.incrby.return_value = 3
        await service.increment("counter", 1)
        client.ttl.assert_not_called()
        client.expire.assert_not_called()

    async def test_incrby_error_returns_zero(
        self, service: RedisService, client: MagicMock
    ) -> None:
        client.incrby.side_effect = RedisError("boom")
        assert await service.increment("counter") == 0
        client.ttl.assert_not_called()

    async def test_expire_error_does_not_hide_value(
        self, service: RedisService, client: MagicMock
    ) -> None:
        client.incrby.return_value = 7
        client.ttl.return_value = -1
        client.expire.side_effect = RedisError("boom")
        assert await service.increment("counter", 1, ttl=60) == 7
