"""Port for probabilistic unique-counting (HyperLogLog). Research §3.3."""

from __future__ import annotations

from typing import Protocol


class ICardinalityService(Protocol):
    """Probabilistic unique counter port."""

    async def add_to_set(self, key: str, *members: str) -> bool:
        """Add members to the probabilistic set.

        Returns ``True`` if the estimated cardinality changed
        (Redis PFADD contract).
        """
        ...

    async def count(self, key: str) -> int:
        """Approximate unique count (±0.81% for HLL)."""
        ...

    async def merge(self, dest: str, *source_keys: str) -> bool:
        """Merge multiple HLLs into ``dest`` (e.g. weekly = ∪ of daily)."""
        ...

    async def set_expire(self, key: str, ttl: int) -> bool:
        """Apply TTL — required so daily/weekly HLLs don't accumulate."""
        ...
