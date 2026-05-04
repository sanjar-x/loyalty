"""TaskIQ tasks + outbox handlers for the Order module — Loyality flow.

Subscribes to:
* Payment events: ``PaymentCapturedEvent``, ``PaymentFailedEvent``.
* DobroPost webhook events: ``DobroPostStatusUpdatedEvent``,
  ``DobroPostPassportInvalidEvent``.
* Russian carrier tracking events: ``RussianCarrierTrackingEvent``.

Plus three cron jobs (stuck-in-CN, hold TTL, return-window-close) on
TaskIQ Beat.

Idempotency: every consumer is wrapped in
:func:`run_inbox_idempotent`, which records the inbound ``event_id``
into the shared ``consumer_inbox`` table (UNIQUE on
``(event_id, consumer)``) before processing. A duplicate delivery
returns early as a no-op.
"""

from __future__ import annotations

import structlog
from dishka.integrations.taskiq import FromDishka, inject
from sqlalchemy.ext.asyncio import AsyncSession

from src.bootstrap.broker import broker
from src.infrastructure.idempotency.runner import run_inbox_idempotent
from src.infrastructure.outbox.relay import register_event_handler
from src.modules.order.application.consumers.logistics_events import (
    DobroPostPassportInvalidConsumer,
    DobroPostStatusUpdatedConsumer,
    RussianCarrierTrackingConsumer,
)
from src.modules.order.application.consumers.payment_events import (
    PaymentCapturedConsumer,
    PaymentFailedConsumer,
)
from src.modules.order.infrastructure.services.cron_jobs import (
    HoldTtlExpiredCanceller,
    ReturnWindowCloser,
    StuckInCnDetector,
)
from src.shared.interfaces.idempotency import IInboxStore

logger = structlog.get_logger(__name__)


def _labels(correlation_id: str | None) -> dict[str, str]:
    return {"correlation_id": correlation_id} if correlation_id else {}


# ---------------------------------------------------------------------------
# TaskIQ tasks (idempotent consumers)
# ---------------------------------------------------------------------------


@broker.task(
    queue="order_consumers",
    exchange="taskiq_rpc_exchange",
    routing_key="order.payment.captured",
    max_retries=3,
    retry_on_error=True,
    timeout=30,
)
@inject
async def order_on_payment_captured_task(
    payload: dict,
    *,
    consumer: FromDishka[PaymentCapturedConsumer],
    inbox: FromDishka[IInboxStore],
    session: FromDishka[AsyncSession],
) -> dict:
    return await run_inbox_idempotent(
        payload=payload,
        consumer_name="order.PaymentCaptured",
        inbox=inbox,
        session=session,
        body=lambda: consumer.handle(payload),
    )


@broker.task(
    queue="order_consumers",
    exchange="taskiq_rpc_exchange",
    routing_key="order.payment.failed",
    max_retries=3,
    retry_on_error=True,
    timeout=30,
)
@inject
async def order_on_payment_failed_task(
    payload: dict,
    *,
    consumer: FromDishka[PaymentFailedConsumer],
    inbox: FromDishka[IInboxStore],
    session: FromDishka[AsyncSession],
) -> dict:
    return await run_inbox_idempotent(
        payload=payload,
        consumer_name="order.PaymentFailed",
        inbox=inbox,
        session=session,
        body=lambda: consumer.handle(payload),
    )


@broker.task(
    queue="order_consumers",
    exchange="taskiq_rpc_exchange",
    routing_key="order.dobropost.status",
    max_retries=3,
    retry_on_error=True,
    timeout=30,
)
@inject
async def order_on_dobropost_status_task(
    payload: dict,
    *,
    consumer: FromDishka[DobroPostStatusUpdatedConsumer],
    inbox: FromDishka[IInboxStore],
    session: FromDishka[AsyncSession],
) -> dict:
    return await run_inbox_idempotent(
        payload=payload,
        consumer_name="order.DobroPostStatus",
        inbox=inbox,
        session=session,
        body=lambda: consumer.handle(payload),
    )


@broker.task(
    queue="order_consumers",
    exchange="taskiq_rpc_exchange",
    routing_key="order.dobropost.passport",
    max_retries=3,
    retry_on_error=True,
    timeout=30,
)
@inject
async def order_on_dobropost_passport_task(
    payload: dict,
    *,
    consumer: FromDishka[DobroPostPassportInvalidConsumer],
    inbox: FromDishka[IInboxStore],
    session: FromDishka[AsyncSession],
) -> dict:
    return await run_inbox_idempotent(
        payload=payload,
        consumer_name="order.DobroPostPassport",
        inbox=inbox,
        session=session,
        body=lambda: consumer.handle(payload),
    )


@broker.task(
    queue="order_consumers",
    exchange="taskiq_rpc_exchange",
    routing_key="order.russian_carrier.status",
    max_retries=3,
    retry_on_error=True,
    timeout=30,
)
@inject
async def order_on_russian_carrier_task(
    payload: dict,
    *,
    consumer: FromDishka[RussianCarrierTrackingConsumer],
    inbox: FromDishka[IInboxStore],
    session: FromDishka[AsyncSession],
) -> dict:
    return await run_inbox_idempotent(
        payload=payload,
        consumer_name="order.RussianCarrierTracking",
        inbox=inbox,
        session=session,
        body=lambda: consumer.handle(payload),
    )


# ---------------------------------------------------------------------------
# Cron jobs (TaskIQ Beat)
# ---------------------------------------------------------------------------


@broker.task(
    queue="order_cron",
    exchange="taskiq_rpc_exchange",
    routing_key="order.cron.stuck_in_cn",
    max_retries=1,
    retry_on_error=True,
    timeout=120,
    schedule=[{"cron": "0 * * * *", "schedule_id": "order_stuck_in_cn_hourly"}],
)
@inject
async def order_stuck_in_cn_cron(
    *,
    detector: FromDishka[StuckInCnDetector],
    session: FromDishka[AsyncSession],
) -> dict:
    held = await detector.run()
    await session.commit()
    return {"held": held}


@broker.task(
    queue="order_cron",
    exchange="taskiq_rpc_exchange",
    routing_key="order.cron.hold_ttl",
    max_retries=1,
    retry_on_error=True,
    timeout=120,
    schedule=[{"cron": "*/15 * * * *", "schedule_id": "order_hold_ttl_15min"}],
)
@inject
async def order_hold_ttl_cron(
    *,
    canceller: FromDishka[HoldTtlExpiredCanceller],
    session: FromDishka[AsyncSession],
) -> dict:
    cancelled = await canceller.run()
    await session.commit()
    return {"cancelled": cancelled}


@broker.task(
    queue="order_cron",
    exchange="taskiq_rpc_exchange",
    routing_key="order.cron.close_window",
    max_retries=1,
    retry_on_error=True,
    timeout=120,
    schedule=[{"cron": "0 4 * * *", "schedule_id": "order_close_window_daily"}],
)
@inject
async def order_close_window_cron(
    *,
    closer: FromDishka[ReturnWindowCloser],
    session: FromDishka[AsyncSession],
) -> dict:
    closed = await closer.run()
    await session.commit()
    return {"closed": closed}


# ---------------------------------------------------------------------------
# Outbox handler registration
# ---------------------------------------------------------------------------


async def _on_payment_captured(
    payload: dict, correlation_id: str | None = None
) -> None:
    await (
        order_on_payment_captured_task.kicker()
        .with_labels(**_labels(correlation_id))
        .kiq(payload=payload)  # ty:ignore[no-matching-overload]
    )


async def _on_payment_failed(payload: dict, correlation_id: str | None = None) -> None:
    await (
        order_on_payment_failed_task.kicker()
        .with_labels(**_labels(correlation_id))
        .kiq(payload=payload)  # ty:ignore[no-matching-overload]
    )


async def _on_dobropost_status(
    payload: dict, correlation_id: str | None = None
) -> None:
    await (
        order_on_dobropost_status_task.kicker()
        .with_labels(**_labels(correlation_id))
        .kiq(payload=payload)  # ty:ignore[no-matching-overload]
    )


async def _on_dobropost_passport(
    payload: dict, correlation_id: str | None = None
) -> None:
    await (
        order_on_dobropost_passport_task.kicker()
        .with_labels(**_labels(correlation_id))
        .kiq(payload=payload)  # ty:ignore[no-matching-overload]
    )


async def _on_russian_carrier(payload: dict, correlation_id: str | None = None) -> None:
    await (
        order_on_russian_carrier_task.kicker()
        .with_labels(**_labels(correlation_id))
        .kiq(payload=payload)  # ty:ignore[no-matching-overload]
    )


register_event_handler("PaymentCapturedEvent", _on_payment_captured)
register_event_handler("PaymentFailedEvent", _on_payment_failed)
register_event_handler("DobroPostStatusUpdatedEvent", _on_dobropost_status)
register_event_handler("DobroPostPassportInvalidEvent", _on_dobropost_passport)
register_event_handler("RussianCarrierTrackingEvent", _on_russian_carrier)
