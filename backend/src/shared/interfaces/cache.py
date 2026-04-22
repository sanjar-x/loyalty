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
        """Delete a key from the cache.

        Args:
            key: Cache key to delete.
        """
        ...

    async def delete_many(self, keys: list[str]) -> None:
        """Delete multiple keys from the cache in a single round-trip.

        Args:
            keys: Cache keys to delete. If empty, this is a no-op.
        """
        ...

    async def get_many(self, keys: list[str]) -> dict[str, str | None]:
        """Retrieve multiple values in a single round-trip.

        Args:
            keys: Cache keys to fetch. If empty, an empty mapping is returned.

        Returns:
            Mapping from key to stored string, or ``None`` for keys that
            do not exist or expired. On cache backend failure every key
            maps to ``None`` (graceful degradation).
        """
        ...

    async def set_many(self, items: dict[str, str], ttl: int = 0) -> None:
        """Store multiple values in a single pipelined round-trip.

        Args:
            items: Mapping of key → value. Empty mapping is a no-op.
            ttl: Time-to-live in seconds applied to every entry.
                ``0`` means no expiration.
        """
        ...

    async def exists(self, key: str) -> bool:
        """Return whether a key currently exists in the cache.

        Returns ``False`` on backend failure (graceful degradation).
        """
        ...

    async def expire(self, key: str, ttl: int) -> bool:
        """Set a new TTL (seconds) on an existing key.

        Args:
            key: Cache key.
            ttl: TTL in seconds. Must be > 0; use :meth:`delete` to remove.

        Returns:
            ``True`` if the key existed and the TTL was applied, ``False``
            otherwise (including backend failure).
        """
        ...

    async def increment(
        self, key: str, amount: int = 1, ttl: int | None = None
    ) -> int:
        """Atomically increment an integer counter.

        If the key does not exist it is initialised to zero before the
        increment. When ``ttl`` is provided and the key has no TTL yet,
        the TTL is applied after the increment (best-effort; not atomic
        with the INCRBY).

        Args:
            key: Cache key.
            amount: Increment delta (may be negative). Default ``1``.
            ttl: Optional TTL in seconds to apply when the key is new.

        Returns:
            The new counter value, or ``0`` on backend failure.
        """
        ...
