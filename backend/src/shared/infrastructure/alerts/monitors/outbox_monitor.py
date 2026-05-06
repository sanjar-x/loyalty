"""Outbox lag monitor (HARD-2).

Scheduled task that runs every 60 seconds via TaskIQ Beat. Surfaces
two failure modes that can stall the relay → consumer pipeline:

* **PENDING backlog growth** — too many ``processed_at IS NULL`` rows.
  Threshold ``> 50`` chosen because the relay batches 100 per minute
  cycle; a backlog above 50 means we are not catching up to inbound
  event volume.
* **Stale pending events** — oldest ``processed_at IS NULL`` row is
  more than 5 minutes behind ``now()``. Threshold matches the typical
  retry budget of consumer handlers and is well above the relay's
  1-minute cycle.

When either threshold trips a single CRITICAL alert is sent. The
monitor is stateless: no per-tick remembrance is needed because the
thresholds are absolute. If the underlying problem persists, the next
tick fires another alert (an intentional cadence — silence is worse
than duplication during an outage).
"""

from __future__ import annotations

from datetime import UTC, datetime

import structlog
from dishka.integrations.taskiq import FromDishka, inject
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.bootstrap.broker import broker
from src.infrastructure.database.models.outbox import OutboxMessage
from src.shared.infrastructure.alerts import (
    AlertLevel,
    TelegramAlerter,
    format_alert,
)

logger = structlog.get_logger(__name__)

_PENDING_BACKLOG_THRESHOLD = 50
_OLDEST_PENDING_THRESHOLD_SECONDS = 5 * 60  # 5 minutes


@broker.task(
    queue="alerts_outbox_monitor",
    exchange="taskiq_rpc_exchange",
    routing_key="alerts.outbox_monitor",
    max_retries=0,
    retry_on_error=False,
    timeout=30,
    schedule=[
        {"cron": "* * * * *", "schedule_id": "alerts_outbox_lag_check_every_minute"},
    ],
)
@inject
async def outbox_lag_check(
    session_factory: FromDishka[async_sessionmaker[AsyncSession]],
) -> dict:
    """Poll outbox state, alert on backlog or stale-pending threshold breach.

    Triggered by TaskIQ Scheduler (Beat) every minute.

    Args:
        session_factory: Injected async session factory.

    Returns:
        Status dict with the metrics observed and whether an alert
        was dispatched. The dict shape is shared with logging /
        debugging — production behaviour is the side-effect alert.
    """
    async with session_factory() as session:
        pending_count, oldest_pending_at = await _read_outbox_state(session)

    now = datetime.now(UTC)
    oldest_age_seconds: float | None = None
    if oldest_pending_at is not None:
        oldest_age_seconds = (now - oldest_pending_at).total_seconds()

    backlog_breach = pending_count > _PENDING_BACKLOG_THRESHOLD
    stale_breach = (
        oldest_age_seconds is not None
        and oldest_age_seconds > _OLDEST_PENDING_THRESHOLD_SECONDS
    )

    if not (backlog_breach or stale_breach):
        return {
            "status": "ok",
            "pending_count": pending_count,
            "oldest_age_seconds": oldest_age_seconds,
            "alert_sent": False,
        }

    body = (
        f"PENDING outbox messages: {pending_count} "
        f"(threshold > {_PENDING_BACKLOG_THRESHOLD})\n"
        f"Oldest pending age: "
        f"{int(oldest_age_seconds) if oldest_age_seconds is not None else 'n/a'}s "
        f"(threshold > {_OLDEST_PENDING_THRESHOLD_SECONDS}s)\n"
        f"Observed at: {now.isoformat()}"
    )
    alerter = TelegramAlerter()
    delivered = await alerter.send(
        format_alert(AlertLevel.CRITICAL, title="Outbox lag", body=body),
    )
    logger.warning(
        "alerts.outbox_lag.threshold_breach",
        pending_count=pending_count,
        oldest_age_seconds=oldest_age_seconds,
        backlog_breach=backlog_breach,
        stale_breach=stale_breach,
        delivered=delivered,
    )
    return {
        "status": "alert",
        "pending_count": pending_count,
        "oldest_age_seconds": oldest_age_seconds,
        "alert_sent": delivered,
    }


async def _read_outbox_state(
    session: AsyncSession,
) -> tuple[int, datetime | None]:
    """Single round-trip to fetch backlog count + oldest pending time."""
    pending_count_stmt = (
        select(func.count())
        .select_from(OutboxMessage)
        .where(OutboxMessage.processed_at.is_(None))
    )
    oldest_pending_stmt = select(func.min(OutboxMessage.created_at)).where(
        OutboxMessage.processed_at.is_(None)
    )
    pending_count = (await session.execute(pending_count_stmt)).scalar_one() or 0
    oldest_pending_at = (
        await session.execute(oldest_pending_stmt)
    ).scalar_one_or_none()
    return int(pending_count), oldest_pending_at
