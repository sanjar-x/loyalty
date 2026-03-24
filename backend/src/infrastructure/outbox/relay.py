"""Outbox Relay: polls unprocessed events and publishes them to the broker.

Implements the Polling Publisher pattern with ``FOR UPDATE SKIP LOCKED``
for concurrency safety -- multiple relay workers can run in parallel
without blocking each other.
"""

from __future__ import annotations

import uuid
from typing import Any, Protocol

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Event handler registry: event_type -> async callable(payload)
# ---------------------------------------------------------------------------


class EventHandler(Protocol):
    """Protocol for outbox event handler callables."""

    async def __call__(
        self, payload: dict[str, Any], *, correlation_id: str | None = None
    ) -> None: ...


_EVENT_HANDLERS: dict[str, EventHandler] = {}


def register_event_handler(event_type: str, handler: EventHandler) -> None:
    """Register a handler for a specific event type.

    Args:
        event_type: The domain event type string (e.g., "BrandLogoUploadInitiatedEvent").
        handler: An async callable that dispatches the event to the broker.
    """
    _EVENT_HANDLERS[event_type] = handler


# ---------------------------------------------------------------------------
# Core relay logic
# ---------------------------------------------------------------------------

# SQL with FOR UPDATE SKIP LOCKED -- multiple workers do not block each other
_FETCH_UNPROCESSED_SQL = text("""
    SELECT id, event_type, payload, correlation_id
    FROM outbox_messages
    WHERE processed_at IS NULL
    ORDER BY created_at ASC
    LIMIT :batch_size
    FOR UPDATE SKIP LOCKED
""")

# Lock a single event for per-event processing
_LOCK_SINGLE_EVENT_SQL = text("""
    SELECT id, event_type, payload, correlation_id
    FROM outbox_messages
    WHERE id = :event_id AND processed_at IS NULL
    FOR UPDATE SKIP LOCKED
""")

_MARK_PROCESSED_SQL = text("""
    UPDATE outbox_messages
    SET processed_at = NOW()
    WHERE id = ANY(:ids)
""")

_MARK_SINGLE_PROCESSED_SQL = text("""
    UPDATE outbox_messages
    SET processed_at = NOW()
    WHERE id = :event_id
""")


async def relay_outbox_batch(
    session_factory: async_sessionmaker[AsyncSession],
    batch_size: int = 100,
) -> int:
    """Fetch a batch of unprocessed outbox events and dispatch them to the broker.

    Each event is processed in its own transaction (per-event isolation),
    so a failure in one event does not affect the rest of the batch.

    Args:
        session_factory: An async session factory for database access.
        batch_size: Maximum number of events to process in one batch.

    Returns:
        The number of successfully processed events.
    """
    # 1. Fetch event IDs to process (short-lived transaction)
    async with session_factory() as session, session.begin():
        result = await session.execute(
            _FETCH_UNPROCESSED_SQL,
            {"batch_size": batch_size},
        )
        rows = result.fetchall()

    if not rows:
        return 0

    # 2. Process each event in its own transaction
    processed = 0
    failed = 0

    for row in rows:
        event_id = row.id
        event_type = row.event_type
        correlation_id = getattr(row, "correlation_id", None) or (
            "relay-" + uuid.uuid4().hex[:12]
        )

        structlog.contextvars.bind_contextvars(
            correlation_id=correlation_id,
            event_id=str(event_id),
            event_type=event_type,
        )

        try:
            async with session_factory() as session, session.begin():
                # Re-lock: verify the event has not been processed by another worker
                locked = await session.execute(
                    _LOCK_SINGLE_EVENT_SQL,
                    {"event_id": event_id},
                )
                event = locked.fetchone()
                if event is None:
                    # Already processed by another worker
                    continue

                handler = _EVENT_HANDLERS.get(event.event_type)
                if handler is None:
                    logger.warning(
                        "Outbox Relay: unknown event_type, skipping",
                        event_type=event.event_type,
                        event_id=str(event_id),
                    )
                    await session.execute(
                        _MARK_SINGLE_PROCESSED_SQL,
                        {"event_id": event_id},
                    )
                    processed += 1
                    continue

                await handler(event.payload, correlation_id=correlation_id)
                await session.execute(
                    _MARK_SINGLE_PROCESSED_SQL,
                    {"event_id": event_id},
                )
                processed += 1

                logger.debug(
                    "Outbox Relay: event dispatched to broker",
                    event_type=event.event_type,
                    event_id=str(event_id),
                )
        except Exception:
            failed += 1
            logger.exception(
                "Outbox Relay: error processing event, skipping",
                event_type=event_type,
                event_id=str(event_id),
            )
            continue

    logger.info(
        "Outbox Relay: batch processed",
        processed=processed,
        failed=failed,
        total_in_batch=len(rows),
    )
    return processed


# ---------------------------------------------------------------------------
# Pruning: delete processed records older than N days
# ---------------------------------------------------------------------------

_PRUNE_SQL = text("""
    DELETE FROM outbox_messages
    WHERE processed_at IS NOT NULL
      AND processed_at < NOW() - INTERVAL '7 days'
""")


async def prune_processed_messages(
    session_factory: async_sessionmaker[AsyncSession],
) -> int:
    """Delete processed outbox records older than 7 days.

    Prevents table bloat and keeps PostgreSQL vacuum efficient.

    Args:
        session_factory: An async session factory for database access.

    Returns:
        The number of deleted rows.
    """
    async with session_factory() as session, session.begin():
        result = await session.execute(_PRUNE_SQL)
        deleted = result.rowcount

    if deleted:
        logger.info("Outbox Pruning: old records deleted", count=deleted)
    return deleted
