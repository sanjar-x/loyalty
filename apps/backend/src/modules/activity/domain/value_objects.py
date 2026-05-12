"""
Activity domain value objects.

Event type taxonomy follows the Snowplow/Segment-inspired schema proposed
in ``Research - Activity Tracking (1) Event-Driven Patterns`` and the
architecture document.
"""

from __future__ import annotations

from enum import StrEnum


class ActivityEventType(StrEnum):
    """Canonical event types recorded by the activity tracker.

    Values are persisted as-is into ``user_activity_events.event_type`` and
    used as Redis counter key suffixes, so they are part of the stable
    public contract.
    """

    PRODUCT_VIEWED = "product_viewed"
    PRODUCT_LIST_VIEWED = "product_list_viewed"
    SEARCH_PERFORMED = "search_performed"
