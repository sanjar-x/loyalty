"""
Redis-backed implementation of :class:`IActivityTracker`.

Architecture (from Research - Activity Tracking Architecture §3 "Hybrid"):

1. Synchronous hot path — push event JSON onto a Redis ``LIST`` and bump
   trending sorted sets in a single pipelined round-trip.  Cost is one
   network round-trip (≈0.1 ms on loopback) and therefore negligible
   for request latency.
2. Every failure is swallowed and logged — analytics must not impact the
   user-facing request.  The caller of :class:`IActivityTracker` can
   therefore omit ``try/except`` blocks.
3. A periodic TaskIQ worker (see ``tasks.flush_activity_events``) drains
   the buffer and persists events into the partitioned PostgreSQL
   ``user_activity_events`` table.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, date, datetime
from typing import Any

import redis.asyncio as redis

from src.shared.interfaces.logger import ILogger

# ---------------------------------------------------------------------------
# Redis key layout — documented in Research - Activity Tracking Architecture §5
# ---------------------------------------------------------------------------

ACTIVITY_QUEUE_KEY = "activity:event_queue"
"""FIFO list of JSON-encoded events awaiting flush to PostgreSQL."""

TRENDING_WEEKLY_KEY = "trending:weekly"
"""Product-level trending scores (weekly window)."""

# TTL for daily sorted sets: keep ~2 days so the nightly popularity job
# can still read yesterday's counts.
_TRENDING_DAILY_TTL_SECONDS = 60 * 60 * 48
_TRENDING_WEEKLY_TTL_SECONDS = 60 * 60 * 24 * 8
_TRENDING_CATEGORY_TTL_SECONDS = 60 * 60 * 24

# Hard cap on the Redis buffer size — prevents uncapped growth if the
# flush worker stalls.  Events beyond this point are dropped with a log
# warning; this is acceptable for at-most-once analytics.
ACTIVITY_QUEUE_SOFT_CAP = 100_000


def trending_daily_key(day: date | None = None) -> str:
    """Return the Redis key for a given day's trending sorted set."""
    day = day or datetime.now(UTC).date()
    return f"trending:daily:{day.isoformat()}"


def trending_category_key(category_id: uuid.UUID) -> str:
    """Return the Redis key for a category-scoped trending sorted set."""
    return f"trending:category:{category_id}"


def search_popular_key() -> str:
    """Return the Redis key for the popular-queries sorted set."""
    return "search:popular_queries"


def search_zero_results_key() -> str:
    """Return the Redis key for queries that returned no results."""
    return "search:zero_results"


class RedisActivityTracker:
    """Fire-and-forget activity tracker backed by Redis + a JSON buffer.

    Implements :class:`IActivityTracker`.
    """

    def __init__(
        self,
        client: redis.Redis,  # type: ignore[type-arg]
        logger: ILogger,
    ) -> None:
        self._client = client
        self._logger = logger.bind(component="RedisActivityTracker")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def track_product_view(
        self,
        *,
        product_id: uuid.UUID,
        category_id: uuid.UUID | None,
        actor_id: uuid.UUID | None,
        session_id: str | None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        payload: dict[str, Any] = {"product_id": str(product_id)}
        if category_id is not None:
            payload["category_id"] = str(category_id)
        if extra:
            payload.update(extra)

        try:
            pipe = self._client.pipeline(transaction=False)
            daily_key = trending_daily_key()
            pipe.zincrby(daily_key, 1.0, str(product_id).encode())
            pipe.expire(daily_key, _TRENDING_DAILY_TTL_SECONDS)
            pipe.zincrby(TRENDING_WEEKLY_KEY, 1.0, str(product_id).encode())
            pipe.expire(TRENDING_WEEKLY_KEY, _TRENDING_WEEKLY_TTL_SECONDS)
            if category_id is not None:
                cat_key = trending_category_key(category_id)
                pipe.zincrby(cat_key, 1.0, str(product_id).encode())
                pipe.expire(cat_key, _TRENDING_CATEGORY_TTL_SECONDS)
            self._enqueue(
                pipe,
                event_type="product_viewed",
                actor_id=actor_id,
                session_id=session_id,
                product_id=product_id,
                category_id=category_id,
                search_query=None,
                payload=payload,
            )
            await pipe.execute()
        except Exception:  # pragma: no cover — defensive
            self._logger.warning(
                "activity_tracking.product_view_failed",
                product_id=str(product_id),
            )

    async def track_product_list_view(
        self,
        *,
        category_id: uuid.UUID | None,
        result_count: int,
        actor_id: uuid.UUID | None,
        session_id: str | None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        payload: dict[str, Any] = {"result_count": int(result_count)}
        if category_id is not None:
            payload["category_id"] = str(category_id)
        if extra:
            payload.update(extra)

        try:
            pipe = self._client.pipeline(transaction=False)
            self._enqueue(
                pipe,
                event_type="product_list_viewed",
                actor_id=actor_id,
                session_id=session_id,
                product_id=None,
                category_id=category_id,
                search_query=None,
                payload=payload,
            )
            await pipe.execute()
        except Exception:  # pragma: no cover — defensive
            self._logger.warning("activity_tracking.plp_view_failed")

    async def track_search(
        self,
        *,
        query: str,
        result_count: int,
        actor_id: uuid.UUID | None,
        session_id: str | None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        normalised = (query or "").strip().lower()
        if not normalised:
            # Never track empty queries — not useful for analytics.
            return

        payload: dict[str, Any] = {
            "query": normalised,
            "result_count": int(result_count),
        }
        if extra:
            payload.update(extra)

        try:
            pipe = self._client.pipeline(transaction=False)
            pipe.zincrby(search_popular_key(), 1.0, normalised.encode())
            pipe.expire(search_popular_key(), _TRENDING_CATEGORY_TTL_SECONDS)
            if result_count == 0:
                pipe.zincrby(search_zero_results_key(), 1.0, normalised.encode())
                pipe.expire(search_zero_results_key(), _TRENDING_CATEGORY_TTL_SECONDS)
            self._enqueue(
                pipe,
                event_type="search_performed",
                actor_id=actor_id,
                session_id=session_id,
                product_id=None,
                category_id=None,
                search_query=normalised,
                payload=payload,
            )
            await pipe.execute()
        except Exception:  # pragma: no cover — defensive
            self._logger.warning("activity_tracking.search_failed")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _enqueue(
        self,
        pipe: redis.client.Pipeline,  # type: ignore[type-arg,name-defined]
        *,
        event_type: str,
        actor_id: uuid.UUID | None,
        session_id: str | None,
        product_id: uuid.UUID | None,
        category_id: uuid.UUID | None,
        search_query: str | None,
        payload: dict[str, Any],
    ) -> None:
        """Serialise the event and append it to the flush buffer.

        Also trims the list to :data:`ACTIVITY_QUEUE_SOFT_CAP` entries to
        prevent runaway memory usage when the flush worker is stalled.
        The cap is applied with ``LTRIM 0 N-1`` which keeps the newest
        events (``LPUSH`` → head).
        """
        event = {
            "id": str(uuid.uuid4()),
            "event_type": event_type,
            "actor_id": str(actor_id) if actor_id else None,
            "session_id": session_id,
            "product_id": str(product_id) if product_id else None,
            "category_id": str(category_id) if category_id else None,
            "search_query": search_query,
            "payload": payload,
            "created_at": datetime.now(UTC).isoformat(),
        }
        pipe.lpush(ACTIVITY_QUEUE_KEY, json.dumps(event, separators=(",", ":")))
        pipe.ltrim(ACTIVITY_QUEUE_KEY, 0, ACTIVITY_QUEUE_SOFT_CAP - 1)
