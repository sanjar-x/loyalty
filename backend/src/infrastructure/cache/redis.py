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
            return value.decode("utf-8") if value else None
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
            logger.warning(
                "Redis read error (GET_MANY)", count=len(keys), error=str(e)
            )
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

    async def increment(
        self, key: str, amount: int = 1, ttl: int | None = None
    ) -> int:
        """Atomically INCRBY ``amount`` on ``key``.

        If ``ttl`` is provided and the key had no prior TTL, the TTL is
        applied afterwards using ``EXPIRE … NX``-like semantics (best
        effort: we skip the EXPIRE call if the key already has a TTL).
        Returns ``0`` on backend failure.
        """
        try:
            logger.debug("Redis INCRBY", key=key, amount=amount)
            new_value = int(await self._client.incrby(key, amount))
        except RedisError as e:
            logger.warning(
                "Redis write error (INCRBY)", key=key, amount=amount, error=str(e)
            )
            return 0

        if ttl is not None and ttl > 0:
            try:
                # -1 means "no expire" in Redis; -2 means "missing" (can't
                # happen right after INCRBY).  Only set TTL when not already
                # configured, so repeated increments don't refresh it.
                current_ttl = await self._client.ttl(key)
                if current_ttl == -1:
                    await self._client.expire(key, ttl)
            except RedisError as e:
                logger.warning(
                    "Redis write error (INCRBY EXPIRE)",
                    key=key,
                    ttl=ttl,
                    error=str(e),
                )

        return new_value
