"""Port for sorted-set operations (leaderboards, trending).

Isolated from ``ICacheService`` per Interface Segregation (research
§3.1): sorted sets are a distinct data model with coordination
semantics that don't belong on a generic cache.
"""

from __future__ import annotations

from typing import Protocol


class ISortedSetService(Protocol):
    """Sorted-set backend port."""

    async def zincrby(
        self, key: str, increment: float, member: str
    ) -> float | None:
        """Atomically increment member's score; create if absent.

        Returns the new score, or ``None`` on backend failure.
        """
        ...

    async def zadd(
        self, key: str, mapping: dict[str, float], *, nx: bool = False
    ) -> int | None:
        """Add members with scores (``nx=True`` for new-only).

        Returns number of new members added, or ``None`` on failure.
        """
        ...

    async def zrevrange(
        self, key: str, start: int, stop: int, *, withscores: bool = False
    ) -> list[tuple[str, float]] | list[str] | None:
        """Top-N members by score, descending.

        ``withscores=True`` yields ``list[(member, score)]``; otherwise
        ``list[member]``. ``None`` on backend failure.
        """
        ...

    async def zscore(self, key: str, member: str) -> float | None:
        """Score of a member, or ``None`` if missing/failure."""
        ...

    async def zrevrank(self, key: str, member: str) -> int | None:
        """0-based rank in DESC order, or ``None`` if missing/failure."""
        ...

    async def zcard(self, key: str) -> int:
        """Cardinality of the sorted set. ``0`` on failure."""
        ...

    async def zremrangebyscore(
        self, key: str, min_score: float, max_score: float
    ) -> int:
        """Remove members whose scores fall inside ``[min, max]``."""
        ...

    async def zrem(self, key: str, *members: str) -> int:
        """Remove named members (needed to evict deactivated items).

        Without this, soft-deleted entities linger in leaderboards
        until the whole key expires.
        """
        ...

    async def zunionstore(
        self,
        dest: str,
        keys: list[str],
        weights: list[float] | None = None,
    ) -> int:
        """Weighted union of sorted sets into ``dest``."""
        ...

    async def set_expire(self, key: str, ttl: int) -> bool:
        """Apply TTL to ``key``. ``True`` if the key existed."""
        ...
