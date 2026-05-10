"""TaskIQ tasks + outbox handlers for the Order module — Loyality flow.

Subscribes to:
* Payment events: ``PaymentCapturedEvent``, ``PaymentFailedEvent``.
* DobroPost webhook events: ``DobroPostStatusUpdatedEvent``,
  ``DobroPostPassportInvalidEvent``.
* Russian carrier tracking events: ``RussianCarrierTrackingEvent``.

Plus three cron jobs (stuck-in-CN, hold TTL, return-window-close) on
TaskIQ Beat.

Idempotency: each TaskIQ task wraps its body via
``run_inbox_idempotent`` (``src.infrastructure.idempotency``) which
records the inbound event_id into the framework-shared ``consumer_inbox``
table (UNIQUE on ``(event_id, consumer)``) before processing. A
duplicate delivery returns early as a no-op (REFACT-001 PR-3a/PR-3b).
"""

from __future__ import annotations

import structlog
from dishka.integrations.taskiq import FromDishka, inject
from sqlalchemy.ext.asyncio import AsyncSession

from src.bootstrap.broker import broker
from src.infrastructure.idempotency import run_inbox_idempotent
from src.infrastructure.outbox.relay import register_event_handler
from src.modules.order.application.consumers.logistics_events import (
    DobroPostPassportInvalidConsumer,
    DobroPostStatusUpdatedConsumer,
    RussianCarrierTrackingConsumer,
)
from src.modules.order.application.consumers.order_procured import (
    OrderProcuredConsumer,
)
from src.modules.order.application.consumers.payment_events import (
    PaymentCapturedConsumer,
    PaymentFailedConsumer,
)
from src.modules.order.application.consumers.telegram_notifications import (
    TelegramOrderNotifier,
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


# ORD-006 (D1.2) — async DobroPost booking after Order is procured.
# ``max_retries=0`` because the underlying ``IDobroPostGateway`` adapter
# already owns its own retry budget + circuit breaker. The consumer
# itself catches gateway exceptions and pivots the Order into
# ``ON_HOLD(BOOKING_FAILED)`` — no point asking TaskIQ to retry on
# top because the consumer has already done its terminal-state work.
@broker.task(
    queue="order_consumers",
    exchange="taskiq_rpc_exchange",
    routing_key="order.procured",
    max_retries=0,
    retry_on_error=False,
    timeout=60,
)
@inject
async def order_on_procured_task(
    payload: dict,
    *,
    consumer: FromDishka[OrderProcuredConsumer],
    inbox: FromDishka[IInboxStore],
    session: FromDishka[AsyncSession],
) -> dict:
    return await run_inbox_idempotent(
        payload=payload,
        consumer_name="order.OrderProcured",
        inbox=inbox,
        session=session,
        body=lambda: consumer.handle(payload),
    )


# T-2 / D3.1 — Telegram push notifications for the customer-facing
# subset of the Order FSM. ``max_retries=2`` so transient Telegram
# 5xx / network errors get a couple of broker-side retries; permanent
# failures (user blocked the bot, chat not found) are swallowed
# inside the adapter so no retry storm hammers the API.
def _telegram_task(routing_key: str):
    """Decorator factory for the five identical-shape Telegram tasks."""

    def decorator(fn):
        return broker.task(
            queue="order_consumers",
            exchange="taskiq_rpc_exchange",
            routing_key=routing_key,
            max_retries=2,
            retry_on_error=True,
            timeout=20,
        )(fn)

    return decorator


@_telegram_task("order.telegram.procured")
@inject
async def telegram_on_order_procured_task(
    payload: dict,
    *,
    consumer: FromDishka[TelegramOrderNotifier],
    inbox: FromDishka[IInboxStore],
    session: FromDishka[AsyncSession],
) -> dict:
    return await run_inbox_idempotent(
        payload=payload,
        consumer_name="order.TelegramOrderProcured",
        inbox=inbox,
        session=session,
        body=lambda: consumer.on_order_procured(payload),
    )


@_telegram_task("order.telegram.arrived_in_ru")
@inject
async def telegram_on_order_arrived_in_ru_task(
    payload: dict,
    *,
    consumer: FromDishka[TelegramOrderNotifier],
    inbox: FromDishka[IInboxStore],
    session: FromDishka[AsyncSession],
) -> dict:
    return await run_inbox_idempotent(
        payload=payload,
        consumer_name="order.TelegramOrderArrivedInRu",
        inbox=inbox,
        session=session,
        body=lambda: consumer.on_order_arrived_in_ru(payload),
    )


@_telegram_task("order.telegram.last_mile")
@inject
async def telegram_on_order_entered_last_mile_task(
    payload: dict,
    *,
    consumer: FromDishka[TelegramOrderNotifier],
    inbox: FromDishka[IInboxStore],
    session: FromDishka[AsyncSession],
) -> dict:
    return await run_inbox_idempotent(
        payload=payload,
        consumer_name="order.TelegramOrderEnteredLastMile",
        inbox=inbox,
        session=session,
        body=lambda: consumer.on_order_entered_last_mile(payload),
    )


@_telegram_task("order.telegram.awaiting_pickup")
@inject
async def telegram_on_order_awaiting_pickup_task(
    payload: dict,
    *,
    consumer: FromDishka[TelegramOrderNotifier],
    inbox: FromDishka[IInboxStore],
    session: FromDishka[AsyncSession],
) -> dict:
    return await run_inbox_idempotent(
        payload=payload,
        consumer_name="order.TelegramOrderAwaitingPickup",
        inbox=inbox,
        session=session,
        body=lambda: consumer.on_order_awaiting_pickup(payload),
    )


@_telegram_task("order.telegram.delivered")
@inject
async def telegram_on_order_delivered_task(
    payload: dict,
    *,
    consumer: FromDishka[TelegramOrderNotifier],
    inbox: FromDishka[IInboxStore],
    session: FromDishka[AsyncSession],
) -> dict:
    return await run_inbox_idempotent(
        payload=payload,
        consumer_name="order.TelegramOrderDelivered",
        inbox=inbox,
        session=session,
        body=lambda: consumer.on_order_delivered(payload),
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


async def _on_order_procured(payload: dict, correlation_id: str | None = None) -> None:
    """ORD-006 (D1.2) — bridge ``OrderProcuredEvent`` → DobroPost booking
    AND T-2 / D3.1 — bridge into the Telegram customer-notification fan-out.
    Both consumers are independent (one books shipment, the other pushes
    a "your parcel is on the way from China" message) and tolerate each
    other's failures via ``run_inbox_idempotent``.
    """
    labels = _labels(correlation_id)
    await (
        order_on_procured_task.kicker().with_labels(**labels).kiq(payload=payload)  # ty:ignore[no-matching-overload]
    )
    await (
        telegram_on_order_procured_task.kicker()
        .with_labels(**labels)
        .kiq(payload=payload)  # ty:ignore[no-matching-overload]
    )


# T-2 / D3.1 — telegram-only bridges for the post-procure FSM events.
async def _on_order_arrived_in_ru_telegram(
    payload: dict, correlation_id: str | None = None
) -> None:
    await (
        telegram_on_order_arrived_in_ru_task.kicker()
        .with_labels(**_labels(correlation_id))
        .kiq(payload=payload)  # ty:ignore[no-matching-overload]
    )


async def _on_order_entered_last_mile_telegram(
    payload: dict, correlation_id: str | None = None
) -> None:
    await (
        telegram_on_order_entered_last_mile_task.kicker()
        .with_labels(**_labels(correlation_id))
        .kiq(payload=payload)  # ty:ignore[no-matching-overload]
    )


async def _on_order_awaiting_pickup_telegram(
    payload: dict, correlation_id: str | None = None
) -> None:
    await (
        telegram_on_order_awaiting_pickup_task.kicker()
        .with_labels(**_labels(correlation_id))
        .kiq(payload=payload)  # ty:ignore[no-matching-overload]
    )


async def _on_order_delivered_telegram(
    payload: dict, correlation_id: str | None = None
) -> None:
    await (
        telegram_on_order_delivered_task.kicker()
        .with_labels(**_labels(correlation_id))
        .kiq(payload=payload)  # ty:ignore[no-matching-overload]
    )


register_event_handler("PaymentCapturedEvent", _on_payment_captured)
register_event_handler("PaymentFailedEvent", _on_payment_failed)
register_event_handler("DobroPostStatusUpdatedEvent", _on_dobropost_status)
register_event_handler("DobroPostPassportInvalidEvent", _on_dobropost_passport)
register_event_handler("RussianCarrierTrackingEvent", _on_russian_carrier)
register_event_handler("OrderProcuredEvent", _on_order_procured)
register_event_handler("OrderArrivedInRuEvent", _on_order_arrived_in_ru_telegram)
register_event_handler(
    "OrderEnteredLastMileEvent", _on_order_entered_last_mile_telegram
)
register_event_handler("OrderAwaitingPickupEvent", _on_order_awaiting_pickup_telegram)
register_event_handler("OrderDeliveredEvent", _on_order_delivered_telegram)
