"""
Activity domain repository interfaces.

Only the persistence contract needed by the flush background task lives
here; the runtime ``IActivityTracker`` port is in ``src.shared.interfaces``
so that any module (primarily ``catalog``) can depend on it without
introducing cross-module coupling at the domain layer.
"""

from __future__ import annotations

from typing import Protocol

from src.modules.activity.domain.entities import UserActivityEvent


class IActivityEventRepository(Protocol):
    """Contract for persisting activity events."""

    async def bulk_add(self, events: list[UserActivityEvent]) -> int:
        """Insert a batch of events, returning the number of inserted rows.

        Implementations should use a single INSERT ... VALUES statement for
        efficiency (append-only workload).
        """
        ...
