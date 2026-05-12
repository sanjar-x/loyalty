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

    async def increment(self, key: str, delta: int = 1, ttl: int = 0) -> int | None:
        """Atomically increment an integer counter.

        If the key does not exist it is initialised to zero before the
        increment. When ``ttl > 0`` is provided and the key is being
        created for the first time, the TTL is applied atomically via a
        Lua script. For existing keys the TTL is left untouched.

        Args:
            key: Cache key.
            delta: Increment amount (may be negative). Default ``1``.
            ttl: Optional TTL in seconds to apply on first creation.
                ``0`` (default) leaves the key without an expiry.

        Returns:
            The new counter value, or ``None`` on backend failure
            (tri-state: callers using the counter for coordination must
            distinguish "0" from "backend unavailable").
        """
        ...

    async def decrement(self, key: str, delta: int = 1) -> int | None:
        """Atomically decrement an integer counter.

        If the key does not exist it is initialised to zero before the
        decrement. Symmetric to :meth:`increment`: ``None`` on backend
        failure.

        Redis: ``DECRBY key delta``.
        """
        ...

    async def set_if_not_exists(
        self, key: str, value: str, ttl: int = 0
    ) -> bool | None:
        """Atomically store the value only if the key does not exist.

        Maps to Redis ``SET key value NX EX ttl``. Intended for
        coordination primitives (idempotency markers, reuse detection,
        best-effort distributed locks).

        Returns:
            * ``True`` — key was absent and the value was written.
            * ``False`` — key already existed; no write performed.
            * ``None`` — backend failure; caller MUST treat this as an
              ambiguous outcome and not infer either branch (research
              RF-1: graceful degradation breaks coordination semantics).
        """
        ...
