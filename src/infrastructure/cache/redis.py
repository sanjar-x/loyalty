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
