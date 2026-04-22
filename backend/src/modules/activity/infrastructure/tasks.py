"""
TaskIQ scheduled tasks for the activity bounded context.

Two tasks are registered with TaskIQ Beat:

* :func:`flush_activity_events_task` — every 5 minutes, drains the Redis
  buffer into the partitioned ``user_activity_events`` table in batches
  of 500.
* :func:`update_product_popularity_task` — daily at 05:00 UTC, recomputes
  ``products.popularity_score`` from the last 30 days of activity data
  so that catalog sort-by-popularity reflects recent demand.
* :func:`ensure_activity_partitions_task` — daily at 01:00 UTC, pre-creates
  the partition for next month if it does not yet exist.  This makes
  partition management a background concern rather than a migration
  concern.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import redis.asyncio as redis
import structlog
from dishka.integrations.taskiq import FromDishka, inject
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.bootstrap.broker import broker
from src.modules.activity.domain.entities import UserActivityEvent
from src.modules.activity.infrastructure.redis_tracker import ACTIVITY_QUEUE_KEY
from src.modules.activity.infrastructure.repository import (
    SqlAlchemyActivityEventRepository,
)

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FLUSH_BATCH_SIZE = 500
"""How many events to pull from the Redis buffer per flush cycle.

Tuned for a ~10–50k events/day scale: with a 5-minute cadence the buffer
is typically a few hundred entries, so a single RPOP loop empties it.
"""

POPULARITY_WINDOW_DAYS = 30
"""Rolling window used by :func:`update_product_popularity_task`."""


# ---------------------------------------------------------------------------
# Parsing helper
# ---------------------------------------------------------------------------


def _parse_event(raw: bytes | str) -> UserActivityEvent | None:
    """Deserialise a single event from the Redis buffer.

    Returns ``None`` for malformed payloads so that a single bad event
    cannot poison the entire batch.
    """
    try:
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        data: dict[str, Any] = json.loads(raw)
        return UserActivityEvent(
            id=uuid.UUID(data["id"]),
            event_type=str(data["event_type"]),
            actor_id=uuid.UUID(data["actor_id"]) if data.get("actor_id") else None,
            session_id=data.get("session_id"),
            product_id=uuid.UUID(data["product_id"])
            if data.get("product_id")
            else None,
            category_id=uuid.UUID(data["category_id"])
            if data.get("category_id")
            else None,
            search_query=data.get("search_query"),
            payload=dict(data.get("payload") or {}),
            created_at=datetime.fromisoformat(data["created_at"]),
        )
    except (ValueError, KeyError, TypeError) as exc:
        logger.warning("activity.flush.skipped_bad_event", error=str(exc))
        return None


# ---------------------------------------------------------------------------
# Flush task: Redis buffer -> PostgreSQL (every 5 minutes)
# ---------------------------------------------------------------------------


@broker.task(
    queue="activity_flush",
    exchange="taskiq_rpc_exchange",
    routing_key="activity.flush",
    max_retries=0,
    retry_on_error=False,
    timeout=240,  # < 5 min cadence so we never overlap with ourselves.
    schedule=[{"cron": "*/5 * * * *", "schedule_id": "activity_flush_every_5min"}],
)
@inject
async def flush_activity_events_task(
    session_factory: FromDishka[async_sessionmaker[AsyncSession]],
    redis_client: FromDishka[redis.Redis],  # type: ignore[type-arg]
) -> dict:
    """Drain the Redis buffer and bulk-insert events into PostgreSQL."""
    raw_events: list[bytes | str] = []
    # RPOP with count would be more efficient but is only available on
    # Redis 6.2+; the simple loop is fine at our current scale.
    for _ in range(FLUSH_BATCH_SIZE):
        item = await redis_client.rpop(ACTIVITY_QUEUE_KEY)
        if item is None:
            break
        raw_events.append(item)

    if not raw_events:
        return {"status": "success", "processed": 0}

    parsed = [e for e in (_parse_event(r) for r in raw_events) if e is not None]

    try:
        async with session_factory() as session:
            repo = SqlAlchemyActivityEventRepository(session)
            inserted = await repo.bulk_add(parsed)
            await session.commit()
        logger.info(
            "activity.flush.success",
            drained=len(raw_events),
            inserted=inserted,
        )
        return {"status": "success", "processed": inserted}
    except Exception:
        # Best-effort re-enqueue so we do not lose data on transient
        # database failures.  Events are idempotent by ``id``.
        logger.exception("activity.flush.failed", count=len(raw_events))
        try:
            if raw_events:
                # Re-enqueue on the SAME side the tracker pushes to so that
                # LTRIM (which keeps the head) cannot immediately discard
                # the requeued batch under buffer pressure.  Reverse the
                # batch so original ordering is preserved once popped via
                # RPOP by the next flush.
                await redis_client.lpush(ACTIVITY_QUEUE_KEY, *reversed(raw_events))
        except Exception:  # pragma: no cover
            logger.exception("activity.flush.requeue_failed")
        return {"status": "error", "processed": 0}


# ---------------------------------------------------------------------------
# Popularity recompute task (daily 05:00 UTC)
# ---------------------------------------------------------------------------


@broker.task(
    queue="activity_popularity",
    exchange="taskiq_rpc_exchange",
    routing_key="activity.popularity",
    max_retries=0,
    retry_on_error=False,
    timeout=600,
    schedule=[
        {"cron": "0 5 * * *", "schedule_id": "activity_popularity_daily"},
    ],
)
@inject
async def update_product_popularity_task(
    session_factory: FromDishka[async_sessionmaker[AsyncSession]],
) -> dict:
    """Recompute ``products.popularity_score`` from recent view counts.

    Two statements in a single transaction:

    1. **Decay** — zero out ``popularity_score`` for products that have
       no ``product_viewed`` events in the last
       :data:`POPULARITY_WINDOW_DAYS`.  Without this step, a product
       that was trending last month keeps its old score forever.
    2. **Refresh** — aggregate the recent view counts and write them
       into ``popularity_score`` for products that have any events.

    If the ``popularity_score`` column does not yet exist (older catalog
    schemas), the task logs a warning and exits gracefully — so it can
    be safely deployed before the catalog migration lands.
    """
    decay_sql = text(
        """
        UPDATE products AS p
           SET popularity_score = 0
         WHERE p.popularity_score > 0
           AND NOT EXISTS (
               SELECT 1 FROM user_activity_events e
                WHERE e.product_id = p.id
                  AND e.event_type = 'product_viewed'
                  AND e.created_at >= :since
           )
        """
    )
    refresh_sql = text(
        """
        UPDATE products AS p
           SET popularity_score = COALESCE(a.view_count, 0)
          FROM (
              SELECT product_id, COUNT(*) AS view_count
                FROM user_activity_events
               WHERE event_type = 'product_viewed'
                 AND product_id IS NOT NULL
                 AND created_at >= :since
            GROUP BY product_id
          ) AS a
         WHERE p.id = a.product_id
           AND p.popularity_score IS DISTINCT FROM a.view_count
        """
    )
    since = datetime.now(UTC) - timedelta(days=POPULARITY_WINDOW_DAYS)
    try:
        async with session_factory() as session:
            decay_result = await session.execute(decay_sql, {"since": since})
            refresh_result = await session.execute(refresh_sql, {"since": since})
            await session.commit()
        decayed = decay_result.rowcount
        refreshed = refresh_result.rowcount
        logger.info(
            "activity.popularity.success", decayed=decayed, refreshed=refreshed
        )
        return {
            "status": "success",
            "rows": decayed + refreshed,
            "decayed": decayed,
            "refreshed": refreshed,
        }
    except Exception as exc:
        # Missing column is benign — log and move on.
        if "popularity_score" in str(exc):
            logger.warning("activity.popularity.column_missing")
            return {"status": "skipped", "rows": 0}
        logger.exception("activity.popularity.failed")
        return {"status": "error", "rows": 0}


# ---------------------------------------------------------------------------
# Partition provisioning (daily 01:00 UTC)
# ---------------------------------------------------------------------------


def _month_bounds(anchor: datetime) -> tuple[datetime, datetime, str]:
    """Return the (start, end_exclusive, suffix) of ``anchor``'s month.

    ``suffix`` is of the form ``YYYYMM`` for use in partition names.
    """
    start = anchor.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if start.month == 12:
        end = start.replace(year=start.year + 1, month=1)
    else:
        end = start.replace(month=start.month + 1)
    return start, end, start.strftime("%Y%m")


@broker.task(
    queue="activity_partitions",
    exchange="taskiq_rpc_exchange",
    routing_key="activity.partitions",
    max_retries=0,
    retry_on_error=False,
    timeout=60,
    schedule=[
        {"cron": "0 1 * * *", "schedule_id": "activity_ensure_partitions_daily"},
    ],
)
@inject
async def ensure_activity_partitions_task(
    session_factory: FromDishka[async_sessionmaker[AsyncSession]],
) -> dict:
    """Ensure partitions for the current + next month exist."""
    now = datetime.now(UTC)
    next_month_anchor = (now.replace(day=28) + timedelta(days=4)).replace(day=1)
    created: list[str] = []
    try:
        async with session_factory() as session:
            for anchor in (now, next_month_anchor):
                start, end, suffix = _month_bounds(anchor)
                partition_name = f"user_activity_events_{suffix}"
                stmt = text(
                    f'CREATE TABLE IF NOT EXISTS "{partition_name}" '
                    f"PARTITION OF user_activity_events "
                    f"FOR VALUES FROM (:start) TO (:end)"
                )
                await session.execute(stmt, {"start": start, "end": end})
                created.append(partition_name)
            await session.commit()
        logger.info("activity.partitions.ensured", partitions=created)
        return {"status": "success", "partitions": created}
    except Exception:
        logger.exception("activity.partitions.failed")
        return {"status": "error", "partitions": []}


# ---------------------------------------------------------------------------
# Co-view scores refresh (hourly)
# ---------------------------------------------------------------------------


CO_VIEW_LOOKBACK_DAYS = 7
"""Source events window for co-view computation."""

CO_VIEW_WINDOW_HOURS = 24
"""Two products are treated as co-viewed when the same actor/session viewed
both within this sliding window."""

CO_VIEW_TOP_PER_PRODUCT = 50
"""Keep only the top-N co-viewed neighbours per product to cap matrix size."""

CO_VIEW_MIN_SCORE = 2
"""Drop weak edges below this threshold to reduce noise."""


@broker.task(
    queue="activity_co_view",
    exchange="taskiq_rpc_exchange",
    routing_key="activity.co_view",
    max_retries=0,
    retry_on_error=False,
    timeout=1800,  # matrix rebuild can take minutes on large corpora
    schedule=[{"cron": "17 * * * *", "schedule_id": "activity_co_view_hourly"}],
)
@inject
async def refresh_co_view_scores_task(
    session_factory: FromDishka[async_sessionmaker[AsyncSession]],
) -> dict:
    """Rebuild ``product_co_view_scores`` from recent activity events.

    Strategy — staging-table swap
    -----------------------------
    The previous implementation did ``TRUNCATE + INSERT`` in a single
    transaction which acquires ``ACCESS EXCLUSIVE`` for the whole
    rebuild (potentially minutes on a large corpus), blocking every
    concurrent "also-viewed" read.  The current strategy rebuilds into
    a staging table that nothing reads from, then performs an atomic
    rename.  Readers see the old matrix the whole time, then — in one
    very short transaction — start seeing the new one:

    1. ``DROP IF EXISTS`` any leftover staging table from a previous
       crashed run, and create a fresh ``product_co_view_scores_new``
       with the same schema (PK, CHECKs, FKs).
    2. Self-join ``user_activity_events`` on actor/session within a
       symmetric ``±CO_VIEW_WINDOW_HOURS`` window to produce both
       directed edges (A→B and B→A) for every observed pair.
    3. Keep the top :data:`CO_VIEW_TOP_PER_PRODUCT` neighbours per
       product with ``score >= CO_VIEW_MIN_SCORE`` and INSERT into the
       staging table, filtered by ``EXISTS (products)`` to avoid
       orphans (FK would otherwise abort the whole rebuild).
    4. Build the read indexes on the staging table.
    5. In a short transaction: ``DROP TABLE`` live, ``ALTER RENAME``
       staging → live, ``ALTER INDEX RENAME`` to restore canonical
       names.  This transaction takes milliseconds regardless of
       matrix size.

    Failure mode: if any step before the swap fails the live matrix
    keeps serving reads.  Staging leftovers are cleaned on the next
    run's step 1.  The swap itself is atomic.
    """
    insert_sql = text(
        f"""
        WITH raw_events AS (
            SELECT
                COALESCE(actor_id::text, session_id) AS viewer,
                product_id,
                created_at
              FROM user_activity_events
             WHERE event_type = 'product_viewed'
               AND product_id IS NOT NULL
               AND COALESCE(actor_id::text, session_id) IS NOT NULL
               AND created_at >= now() - interval '{CO_VIEW_LOOKBACK_DAYS} days'
        ),
        pair_views AS (
            SELECT
                a.product_id    AS product_id,
                b.product_id    AS co_product_id,
                a.viewer        AS viewer
              FROM raw_events AS a
              JOIN raw_events AS b
                ON a.viewer = b.viewer
               AND a.product_id <> b.product_id
               AND b.created_at BETWEEN a.created_at - interval '{CO_VIEW_WINDOW_HOURS} hours'
                                    AND a.created_at + interval '{CO_VIEW_WINDOW_HOURS} hours'
        ),
        pair_scores AS (
            SELECT
                product_id,
                co_product_id,
                COUNT(DISTINCT viewer) AS score
              FROM pair_views
          GROUP BY product_id, co_product_id
            HAVING COUNT(DISTINCT viewer) >= :min_score
        ),
        top_pairs AS (
            SELECT product_id, co_product_id, score
              FROM (
                SELECT
                    product_id,
                    co_product_id,
                    score,
                    ROW_NUMBER() OVER (
                        PARTITION BY product_id
                        ORDER BY score DESC, co_product_id
                    ) AS rn
                  FROM pair_scores
              ) ranked
             WHERE rn <= :top_n
        )
        INSERT INTO product_co_view_scores_new (product_id, co_product_id, score, computed_at)
            SELECT t.product_id, t.co_product_id, t.score::int, now()
              FROM top_pairs t
             WHERE EXISTS (SELECT 1 FROM products p WHERE p.id = t.product_id)
               AND EXISTS (SELECT 1 FROM products p WHERE p.id = t.co_product_id)
        """
    )

    create_staging_sql = text(
        """
        DROP TABLE IF EXISTS product_co_view_scores_new;
        CREATE TABLE product_co_view_scores_new (
            product_id UUID NOT NULL,
            co_product_id UUID NOT NULL,
            score INTEGER NOT NULL,
            computed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT pk_product_co_view_scores_new
                PRIMARY KEY (product_id, co_product_id),
            CONSTRAINT ck_product_co_view_scores_new_distinct
                CHECK (product_id <> co_product_id),
            CONSTRAINT ck_product_co_view_scores_new_positive
                CHECK (score > 0),
            CONSTRAINT fk_product_co_view_scores_new_product
                FOREIGN KEY (product_id) REFERENCES products (id)
                ON DELETE CASCADE,
            CONSTRAINT fk_product_co_view_scores_new_co_product
                FOREIGN KEY (co_product_id) REFERENCES products (id)
                ON DELETE CASCADE
        );
        """
    )

    create_indexes_sql = text(
        """
        CREATE INDEX ix_product_co_view_scores_new_top
            ON product_co_view_scores_new (product_id, score DESC);
        CREATE INDEX ix_product_co_view_scores_new_computed_at
            ON product_co_view_scores_new (computed_at);
        """
    )

    swap_sql = text(
        """
        DROP TABLE product_co_view_scores;
        ALTER TABLE product_co_view_scores_new
            RENAME TO product_co_view_scores;
        ALTER INDEX ix_product_co_view_scores_new_top
            RENAME TO ix_product_co_view_scores_top;
        ALTER INDEX ix_product_co_view_scores_new_computed_at
            RENAME TO ix_product_co_view_scores_computed_at;
        ALTER TABLE product_co_view_scores
            RENAME CONSTRAINT pk_product_co_view_scores_new
                          TO pk_product_co_view_scores;
        ALTER TABLE product_co_view_scores
            RENAME CONSTRAINT ck_product_co_view_scores_new_distinct
                          TO ck_product_co_view_scores_distinct;
        ALTER TABLE product_co_view_scores
            RENAME CONSTRAINT ck_product_co_view_scores_new_positive
                          TO ck_product_co_view_scores_positive;
        ALTER TABLE product_co_view_scores
            RENAME CONSTRAINT fk_product_co_view_scores_new_product
                          TO fk_product_co_view_scores_product;
        ALTER TABLE product_co_view_scores
            RENAME CONSTRAINT fk_product_co_view_scores_new_co_product
                          TO fk_product_co_view_scores_co_product;
        """
    )

    try:
        async with session_factory() as session:
            # Steps 1-4: build staging in its own transaction.  If any
            # step raises, the live table is untouched.
            await session.execute(create_staging_sql)
            result = await session.execute(
                insert_sql,
                {
                    "min_score": CO_VIEW_MIN_SCORE,
                    "top_n": CO_VIEW_TOP_PER_PRODUCT,
                },
            )
            rows = result.rowcount
            await session.execute(create_indexes_sql)
            await session.commit()

            # Step 5: atomic swap — very short transaction.  Readers
            # see the old matrix up to this point, then the new one.
            await session.execute(swap_sql)
            await session.commit()
        logger.info("activity.co_view.success", rows=rows)
        return {"status": "success", "rows": rows}
    except Exception as exc:
        # Missing table is benign — e.g. migration not yet applied.
        message = str(exc)
        if (
            "product_co_view_scores" in message
            and "does not exist" in message.lower()
        ):
            logger.warning("activity.co_view.table_missing")
            return {"status": "skipped", "rows": 0}
        logger.exception("activity.co_view.failed")
        return {"status": "error", "rows": 0}
