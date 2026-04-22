"""
Activity domain entities.

``UserActivityEvent`` is a *lightweight* analytics record — it is NOT a
business aggregate (no invariants, no transitions, no domain events).
Therefore it does not inherit from ``AggregateRoot``; instead it is a
plain frozen ``attrs`` entity that flows from Redis buffer into a
partitioned PostgreSQL table via a background task.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import attrs

from src.modules.activity.domain.value_objects import ActivityEventType


@attrs.define(frozen=True, slots=True)
class UserActivityEvent:
    """An immutable activity record.

    Attributes:
        id: Unique event identifier (also used for idempotency).
        event_type: One of :class:`ActivityEventType`.
        actor_id: Authenticated identity UUID, or ``None`` for anonymous.
        session_id: Opaque session identifier (cookie or Telegram hash).
        product_id: Denormalized product reference (nullable).
        category_id: Denormalized category reference (nullable).
        search_query: Normalised search query (nullable).
        payload: Event-specific extras stored as JSONB.
        created_at: Event timestamp in UTC.
    """

    id: uuid.UUID
    event_type: str
    actor_id: uuid.UUID | None
    session_id: str | None
    product_id: uuid.UUID | None
    category_id: uuid.UUID | None
    search_query: str | None
    payload: dict[str, Any]
    created_at: datetime

    @classmethod
    def create(
        cls,
        *,
        event_type: ActivityEventType | str,
        actor_id: uuid.UUID | None = None,
        session_id: str | None = None,
        product_id: uuid.UUID | None = None,
        category_id: uuid.UUID | None = None,
        search_query: str | None = None,
        payload: dict[str, Any] | None = None,
        created_at: datetime | None = None,
    ) -> UserActivityEvent:
        """Factory producing a new activity event with a fresh id/timestamp."""
        return cls(
            id=uuid.uuid4(),
            event_type=str(event_type),
            actor_id=actor_id,
            session_id=session_id,
            product_id=product_id,
            category_id=category_id,
            search_query=search_query,
            payload=payload or {},
            created_at=created_at or datetime.now(UTC),
        )
