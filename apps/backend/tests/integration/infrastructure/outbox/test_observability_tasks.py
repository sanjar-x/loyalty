"""Integration tests for the outbox observability cron tasks (D2.1, D2.2)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.failed_task import FailedTask
from src.infrastructure.database.models.outbox import OutboxMessage
from src.infrastructure.outbox.tasks import (
    _DLQ_GROWTH_SQL,
    _DLQ_WINDOW_MINUTES,
    _OUTBOX_LAG_SQL,
    _OUTBOX_LAG_WARNING_THRESHOLD_S,
)

pytestmark = pytest.mark.integration


async def _seed_outbox_row(
    db_session: AsyncSession,
    *,
    created_at: datetime,
    processed_at: datetime | None = None,
) -> OutboxMessage:
    row = OutboxMessage(
        id=uuid.uuid4(),
        aggregate_type="test",
        aggregate_id=str(uuid.uuid4()),
        event_type="TestEvent",
        payload={"hi": "there"},
        created_at=created_at,
        processed_at=processed_at,
    )
    db_session.add(row)
    await db_session.flush()
    return row


async def _seed_failed_task(
    db_session: AsyncSession,
    *,
    task_name: str,
    failed_at: datetime,
) -> FailedTask:
    row = FailedTask(
        id=uuid.uuid4(),
        task_id=f"task-{uuid.uuid4().hex[:8]}",
        task_name=task_name,
        args={},
        labels={},
        error_message="test failure",
        retry_count=3,
        failed_at=failed_at,
    )
    db_session.add(row)
    await db_session.flush()
    return row


# ---------------------------------------------------------------------------
# D2.1 — outbox lag SELECT contract
# ---------------------------------------------------------------------------


async def test_outbox_lag_zero_when_no_pending(db_session: AsyncSession) -> None:
    # Processed-only rows shouldn't contribute to lag.
    await _seed_outbox_row(
        db_session,
        created_at=datetime.now(UTC) - timedelta(hours=1),
        processed_at=datetime.now(UTC),
    )
    row = (await db_session.execute(_OUTBOX_LAG_SQL)).one()
    # MIN(NULL) → NULL → COALESCE-via-cast yields NULL; the cron task
    # collapses None to 0 explicitly. Replicate that here.
    assert row.lag_seconds is None or int(row.lag_seconds) == 0
    assert int(row.pending_count) == 0


async def test_outbox_lag_picks_oldest_pending(db_session: AsyncSession) -> None:
    """The query must report the OLDEST unprocessed event, not an
    average — a single slow consumer surfaces the moment its event
    crosses the threshold."""
    now = datetime.now(UTC)
    await _seed_outbox_row(db_session, created_at=now - timedelta(seconds=30))
    old_row = await _seed_outbox_row(
        db_session,
        created_at=now - timedelta(seconds=_OUTBOX_LAG_WARNING_THRESHOLD_S + 30),
    )

    row = (await db_session.execute(_OUTBOX_LAG_SQL)).one()
    assert int(row.pending_count) == 2
    # Slack — actual NOW() inside the SQL adds a few ms.
    assert int(row.lag_seconds) >= _OUTBOX_LAG_WARNING_THRESHOLD_S
    # The lag is anchored on the oldest row's created_at.
    expected_min = (datetime.now(UTC) - old_row.created_at).total_seconds()
    assert abs(int(row.lag_seconds) - int(expected_min)) <= 5


# ---------------------------------------------------------------------------
# D2.2 — DLQ growth SELECT contract
# ---------------------------------------------------------------------------


async def test_dlq_growth_breakdown_groups_by_task_name(
    db_session: AsyncSession,
) -> None:
    now = datetime.now(UTC)
    fresh = now - timedelta(minutes=5)
    too_old = now - timedelta(minutes=_DLQ_WINDOW_MINUTES + 5)

    # 3 of task A in-window, 2 of task B in-window, 1 of A out-of-window.
    for _ in range(3):
        await _seed_failed_task(db_session, task_name="task.A", failed_at=fresh)
    for _ in range(2):
        await _seed_failed_task(db_session, task_name="task.B", failed_at=fresh)
    await _seed_failed_task(db_session, task_name="task.A", failed_at=too_old)

    rows = (
        await db_session.execute(
            _DLQ_GROWTH_SQL, {"window_minutes": str(_DLQ_WINDOW_MINUTES)}
        )
    ).all()
    breakdown = {row.task_name: int(row.failures) for row in rows}

    # Out-of-window row excluded; ordering is by failures DESC.
    assert breakdown == {"task.A": 3, "task.B": 2}
    assert rows[0].task_name == "task.A"
