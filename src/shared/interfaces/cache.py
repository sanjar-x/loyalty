"""
Cache service port (Hexagonal Architecture).

Defines the ``ICacheService`` protocol for key-value caching.
The concrete implementation (Redis) lives in the infrastructure layer.

Typical usage:
    class MyHandler:
        def __init__(self, cache: ICacheService) -> None:
            self._cache = cache

        async def run(self) -> str | None:
            return await self._cache.get("my-key")
"""

from typing import Protocol


class ICacheService(Protocol):
    """Contract for key-value cache operations."""

    async def set(self, key: str, value: str, ttl: int = 0) -> None:
        """Store a value under the given key.

        Args:
            key: Cache key.
            value: String value to store.
            ttl: Time-to-live in seconds. 0 means no expiration.
        """
        ...

    async def get(self, key: str) -> str | None:
        """Retrieve a value by key.

        Args:
            key: Cache key.

        Returns:
            The stored string, or None if the key does not exist or has expired.
        """
        ...

    async def delete(self, key: str) -> None:
        """Remove a key from the cache.

        Args:
            key: Cache key to delete.
        """
        ...
