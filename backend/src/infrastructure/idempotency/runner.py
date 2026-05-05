"""Inbox-protected runner for TaskIQ consumer tasks.

Every cross-module event consumer wraps its body in
:func:`run_inbox_idempotent` so that repeated deliveries of the same
outbox event become no-ops at the business-effect level.

The helper is generic and module-independent: it takes only an
``IInboxStore``, an ``AsyncSession`` (so the inbox row commits with
the work), the consumer's name (used as the discriminator in the
``consumer_inbox.consumer`` column), and a callable that performs
the actual work.
"""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from src.shared.interfaces.idempotency import IInboxStore

logger = structlog.get_logger(__name__)


def _extract_event_id(payload: dict) -> uuid.UUID | None:
    raw = payload.get("event_id")
    if raw is None:
        return None
    try:
        return uuid.UUID(str(raw))
    except TypeError, ValueError:
        return None


async def run_inbox_idempotent(
    *,
    payload: dict,
    consumer_name: str,
    inbox: IInboxStore,
    session: AsyncSession,
    body: Callable[[], Awaitable[None]],
) -> dict:
    """Inbox-protected wrapper for a TaskIQ consumer.

    1. Extracts ``event_id`` from the payload (every outbox event
       carries one — :class:`DomainEvent` base class).
    2. Calls :meth:`IInboxStore.try_record`. If the record already
       exists, the helper returns ``{"status": "ok", "deduplicated":
       True}`` without invoking ``body``.
    3. Otherwise runs ``body`` and commits the session, persisting both
       the inbox row and the business mutation atomically.

    If the payload does not carry an ``event_id`` (legacy / malformed
    event), the helper falls back to non-idempotent execution rather
    than silently dropping the event — a structured ``warning`` log is
    emitted so the gap surfaces in observability.
    """
    event_id = _extract_event_id(payload)
    if event_id is None:
        logger.warning(
            "inbox.no_event_id",
            consumer=consumer_name,
            payload_keys=sorted(payload.keys()),
        )
        await body()
        await session.commit()
        return {"status": "ok", "deduplicated": False}

    recorded = await inbox.try_record(event_id=event_id, consumer=consumer_name)
    if not recorded:
        logger.info(
            "inbox.duplicate",
            consumer=consumer_name,
            event_id=str(event_id),
        )
        return {"status": "ok", "deduplicated": True}

    await body()
    await session.commit()
    return {"status": "ok", "deduplicated": False}
