"""Failed-tasks (DLQ) growth monitor (HARD-2).

Scheduled task that runs every minute via TaskIQ Beat. Detects new
rows landing in the ``failed_tasks`` table since the previous tick
and dispatches a single WARNING alert per detected growth.

State tracking is **per-worker-process**: a module-level
``_last_seen_failed_at`` records the most recent ``failed_at``
timestamp the monitor has observed. On worker restart the state
resets and the next tick sees every existing row as "new" — that is
acceptable; an extra alert on restart is cheaper than persisting
state for a low-volume signal.

Cadence note: TaskIQ schedule cron supports per-minute granularity;
the proposed 30-second interval from the original spec would require
a custom interval source, so we settle for 60s here. Alert latency
goes from ~30s to ~60s, well within the operational tolerance.
"""

from __future__ import annotations

from datetime import datetime

import structlog
from dishka.integrations.taskiq import FromDishka, inject
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.bootstrap.broker import broker
from src.infrastructure.database.models.failed_task import FailedTask
from src.shared.infrastructure.alerts import (
    AlertLevel,
    TelegramAlerter,
    format_alert,
)

logger = structlog.get_logger(__name__)

# Per-process state. See module docstring for the restart-amplification
# tradeoff that motivates not persisting this.
_last_seen_failed_at: datetime | None = None


@broker.task(
    queue="alerts_failed_tasks_monitor",
    exchange="taskiq_rpc_exchange",
    routing_key="alerts.failed_tasks_monitor",
    max_retries=0,
    retry_on_error=False,
    timeout=30,
    schedule=[
        {
            "cron": "* * * * *",
            "schedule_id": "alerts_failed_tasks_growth_every_minute",
        },
    ],
)
@inject
async def failed_tasks_growth_check(
    session_factory: FromDishka[async_sessionmaker[AsyncSession]],
) -> dict:
    """Poll failed_tasks; alert on new rows since last tick.

    Triggered by TaskIQ Scheduler (Beat) every minute.

    Args:
        session_factory: Injected async session factory.

    Returns:
        Status dict with row count + the new ``failed_at`` watermark.
    """
    global _last_seen_failed_at

    async with session_factory() as session:
        latest_failed_at, total_count = await _read_failed_tasks_watermark(session)

    new_rows_seen = latest_failed_at is not None and (
        _last_seen_failed_at is None or latest_failed_at > _last_seen_failed_at
    )

    if not new_rows_seen:
        return {
            "status": "ok",
            "total_count": total_count,
            "latest_failed_at": latest_failed_at.isoformat()
            if latest_failed_at is not None
            else None,
            "alert_sent": False,
        }

    # Count rows that are strictly newer than the last watermark we held.
    async with session_factory() as session:
        new_count = await _count_new_failures(session, since=_last_seen_failed_at)

    body = (
        f"New failed_tasks rows since last tick: {new_count}\n"
        f"Total failed_tasks (all task_names): {total_count}\n"
        f"Latest failed_at: "
        f"{latest_failed_at.isoformat() if latest_failed_at else 'n/a'}\n"
        f"(Inspect via: SELECT task_name, error_message, failed_at "
        f"FROM failed_tasks ORDER BY failed_at DESC LIMIT 10;)"
    )
    alerter = TelegramAlerter()
    delivered = await alerter.send(
        format_alert(AlertLevel.WARNING, title="DLQ growth", body=body),
    )
    logger.warning(
        "alerts.failed_tasks.growth_detected",
        new_count=new_count,
        total_count=total_count,
        latest_failed_at=latest_failed_at.isoformat() if latest_failed_at else None,
        delivered=delivered,
    )

    _last_seen_failed_at = latest_failed_at
    return {
        "status": "alert",
        "total_count": total_count,
        "new_count": new_count,
        "latest_failed_at": latest_failed_at.isoformat() if latest_failed_at else None,
        "alert_sent": delivered,
    }


async def _read_failed_tasks_watermark(
    session: AsyncSession,
) -> tuple[datetime | None, int]:
    """One round-trip — max(failed_at) + total row count."""
    stmt = select(func.max(FailedTask.failed_at), func.count()).select_from(FailedTask)
    row = (await session.execute(stmt)).one()
    latest_failed_at = row[0]
    total_count = int(row[1] or 0)
    return latest_failed_at, total_count


async def _count_new_failures(
    session: AsyncSession,
    *,
    since: datetime | None,
) -> int:
    """Count failed_tasks rows whose ``failed_at`` exceeds the watermark."""
    stmt = select(func.count()).select_from(FailedTask)
    if since is not None:
        stmt = stmt.where(FailedTask.failed_at > since)
    return int((await session.execute(stmt)).scalar_one() or 0)
