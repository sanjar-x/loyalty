"""Port for event-buffer / FIFO queue operations (research §3.2).

Backed by Redis Lists in the default implementation; could be swapped
for Streams without touching callers.
"""

from __future__ import annotations

from typing import Protocol


class IEventBufferService(Protocol):
    """FIFO event buffer port."""

    async def push(self, key: str, *values: str) -> int | None:
        """Append values; returns new length or ``None`` on failure."""
        ...

    async def pop_batch(self, key: str, count: int) -> list[str]:
        """Pop up to ``count`` values from the head (FIFO).

        Returns an empty list if the buffer is empty or the backend
        fails — callers must treat ``[]`` as "nothing to process".
        """
        ...

    async def length(self, key: str) -> int:
        """Current buffer length. ``0`` on failure."""
        ...

    async def set_expire(self, key: str, ttl: int) -> bool:
        """Apply TTL; required so buffers without consumers don't grow
        unbounded. ``True`` if the key existed.
        """
        ...
