"""Redis-backed implementation of the ICacheService interface.

Provides basic key-value operations (set, get, delete) with graceful
error handling -- cache failures are logged but never propagate to
the caller.
"""

import redis.asyncio as redis
import structlog
from redis.exceptions import RedisError

from src.shared.interfaces.cache import ICacheService

logger = structlog.get_logger("redis")


class RedisService(ICacheService):
    """Cache service implementation backed by an async Redis client."""

    def __init__(self, client: redis.Redis):
        """Initialize the service with an async Redis client.

        Args:
            client: An async Redis client instance.
        """
        self._client = client

    async def set(self, key: str, value: str, ttl: int = 0) -> None:
        """Store a value in Redis with an optional TTL.

        Args:
            key: The cache key.
            value: The string value to store.
            ttl: Time-to-live in seconds. 0 means no expiration.
        """
        try:
            logger.debug("Redis SET", key=key)
            await self._client.set(key, value, ex=ttl if ttl > 0 else None)
        except RedisError as e:
            logger.warning("Redis write error (SET)", key=key, error=str(e))

    async def get(self, key: str) -> str | None:
        """Retrieve a value from Redis by key.

        Args:
            key: The cache key to look up.

        Returns:
            The cached string value, or None if the key does not exist
            or a Redis error occurs.
        """
        try:
            logger.debug("Redis GET", key=key)
            value = await self._client.get(key)
            if value is None:
                return None
            if isinstance(value, bytes):
                return value.decode("utf-8")
            return str(value)
        except RedisError as e:
            logger.warning("Redis read error (GET)", key=key, error=str(e))
            return None

    async def delete(self, key: str) -> None:
        """Delete a key from Redis.

        Args:
            key: The cache key to delete.
        """
        try:
            logger.debug("Redis DELETE", key=key)
            await self._client.delete(key)
        except RedisError as e:
            logger.warning("Redis delete error (DELETE)", key=key, error=str(e))

    async def delete_many(self, keys: list[str]) -> None:
        """Delete multiple keys from Redis in a single round-trip.

        Args:
            keys: The cache keys to delete. If empty, this is a no-op.
        """
        if not keys:
            return
        try:
            logger.debug("Redis DELETE_MANY", count=len(keys))
            await self._client.delete(*keys)
        except RedisError as e:
            logger.warning(
                "Redis delete error (DELETE_MANY)", count=len(keys), error=str(e)
            )

    async def get_many(self, keys: list[str]) -> dict[str, str | None]:
        """Retrieve multiple values in one MGET round-trip.

        Returns a mapping where missing keys map to ``None``. On Redis
        failure every key maps to ``None`` (graceful degradation).
        """
        if not keys:
            return {}
        try:
            logger.debug("Redis GET_MANY", count=len(keys))
            raw = await self._client.mget(keys)
        except RedisError as e:
            logger.warning("Redis read error (GET_MANY)", count=len(keys), error=str(e))
            return {key: None for key in keys}

        result: dict[str, str | None] = {}
        for key, value in zip(keys, raw, strict=True):
            if value is None:
                result[key] = None
            elif isinstance(value, bytes):
                result[key] = value.decode("utf-8")
            else:
                result[key] = str(value)
        return result

    async def set_many(self, items: dict[str, str], ttl: int = 0) -> None:
        """Store multiple values in one pipelined round-trip.

        When ``ttl > 0`` every key gets the same TTL; otherwise keys are
        stored without expiration. MSET does not support TTL per-key, so
        we use a pipeline of ``SET key value EX ttl`` commands.
        """
        if not items:
            return
        try:
            logger.debug("Redis SET_MANY", count=len(items), ttl=ttl)
            if ttl > 0:
                pipe = self._client.pipeline(transaction=False)
                for key, value in items.items():
                    pipe.set(key, value, ex=ttl)
                await pipe.execute()
            else:
                await self._client.mset(items)
        except RedisError as e:
            logger.warning(
                "Redis write error (SET_MANY)", count=len(items), error=str(e)
            )

    async def exists(self, key: str) -> bool:
        """Return whether ``key`` is present. ``False`` on backend error."""
        try:
            logger.debug("Redis EXISTS", key=key)
            return bool(await self._client.exists(key))
        except RedisError as e:
            logger.warning("Redis read error (EXISTS)", key=key, error=str(e))
            return False

    async def expire(self, key: str, ttl: int) -> bool:
        """Apply a new TTL (seconds) to an existing key."""
        if ttl <= 0:
            return False
        try:
            logger.debug("Redis EXPIRE", key=key, ttl=ttl)
            return bool(await self._client.expire(key, ttl))
        except RedisError as e:
            logger.warning("Redis write error (EXPIRE)", key=key, error=str(e))
            return False

    # Lua: INCRBY, then EXPIRE only if the key was just created
    # (INCRBY returns exactly the delta when creating from zero).  Atomic
    # single round-trip, immune to process-death between INCR and EXPIRE.
    _INCR_WITH_TTL_LUA = """
    local v = redis.call('INCRBY', KEYS[1], ARGV[1])
    if v == tonumber(ARGV[1]) and tonumber(ARGV[2]) > 0 then
        redis.call('EXPIRE', KEYS[1], ARGV[2])
    end
    return v
    """

    async def increment(self, key: str, delta: int = 1, ttl: int = 0) -> int | None:
        """Atomically INCRBY ``delta`` on ``key``.

        When ``ttl > 0`` the EXPIRE is applied atomically via a Lua
        script, only on the INCR that creates the key (prevents
        immortal counters when a process dies between INCR and EXPIRE).

        Returns ``None`` on backend failure (tri-state: callers must
        distinguish 0 from "backend unavailable").
        """
        try:
            logger.debug("Redis INCRBY", key=key, delta=delta, ttl=ttl)
            if ttl > 0:
                raw = await self._client.eval(
                    self._INCR_WITH_TTL_LUA, 1, key, delta, ttl
                )
            else:
                raw = await self._client.incrby(key, delta)
            return int(raw)
        except RedisError as e:
            logger.warning(
                "Redis write error (INCRBY)", key=key, delta=delta, error=str(e)
            )
            return None

    async def decrement(self, key: str, delta: int = 1) -> int | None:
        """Atomically DECRBY ``delta`` on ``key``.

        Symmetric to :meth:`increment`; returns ``None`` on backend
        failure.
        """
        try:
            logger.debug("Redis DECRBY", key=key, delta=delta)
            return int(await self._client.decrby(key, delta))
        except RedisError as e:
            logger.warning(
                "Redis write error (DECRBY)", key=key, delta=delta, error=str(e)
            )
            return None

    async def set_if_not_exists(
        self, key: str, value: str, ttl: int = 0
    ) -> bool | None:
        """Atomic SET NX [EX ttl].

        Returns:
            * ``True`` — value written (key was absent).
            * ``False`` — key already existed.
            * ``None`` — backend failure (ambiguous; caller MUST NOT
              infer either branch).
        """
        try:
            logger.debug("Redis SET NX", key=key, ttl=ttl)
            result = await self._client.set(
                key, value, nx=True, ex=ttl if ttl > 0 else None
            )
        except RedisError as e:
            logger.warning("Redis write error (SET NX)", key=key, error=str(e))
            return None
        # redis-py returns True on success, None on "NX not satisfied".
        return bool(result)
