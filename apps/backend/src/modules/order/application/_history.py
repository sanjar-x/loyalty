"""Internal helpers for writing Order state-history entries from command
handlers (audit trail per research (2) §10.2 / §15.6).

The helper consumes the events accumulated on an aggregate via
``add_domain_event`` and writes a corresponding row into
``order_state_history``. It only emits a row for events that are
*FSM transitions* — informational events (PaymentIntent attached, pickup
point changed, item-shipment id assigned) are skipped. The UNIQUE
constraint on ``event_id`` makes the call idempotent — replays
(e.g. via consumer retry) cause IntegrityError on the second insert,
which the writer turns into a silent rollback of the duplicate row.
"""

from __future__ import annotations

import uuid
from dataclasses import asdict
from datetime import UTC, datetime

from src.modules.order.domain.entities import Order
from src.modules.order.domain.interfaces import (
    HistoryActor,
    IOrderStateHistoryWriter,
)
from src.modules.order.domain.value_objects import OrderStatus

_FSM_EVENT_TO_STATUS: dict[str, OrderStatus] = {
    "OrderCreatedEvent": OrderStatus.PENDING,
    "OrderPaidEvent": OrderStatus.PAID,
    "OrderProcuredEvent": OrderStatus.PROCURED,
    "OrderArrivedInRuEvent": OrderStatus.ARRIVED_IN_RU,
    "OrderEnteredLastMileEvent": OrderStatus.IN_LAST_MILE,
    "OrderAwaitingPickupEvent": OrderStatus.AWAITING_PICKUP,
    "OrderDeliveredEvent": OrderStatus.DELIVERED,
    "OrderClosedEvent": OrderStatus.CLOSED,
    "OrderEnteredHoldEvent": OrderStatus.ON_HOLD,
    "OrderReturningToWarehouseEvent": OrderStatus.RETURNING_TO_RU_WAREHOUSE,
    "OrderNotDeliveredEvent": OrderStatus.NOT_DELIVERED,
    "OrderReturnRequestedEvent": OrderStatus.RETURN_IN_PROGRESS,
    "OrderReturnedEvent": OrderStatus.RETURNED,
    "OrderCancelledEvent": OrderStatus.CANCELLED,
}


async def record_history(
    *,
    order: Order,
    history_writer: IOrderStateHistoryWriter,
    actor: HistoryActor,
    pre_commit_status: OrderStatus | None,
) -> None:
    """Append history rows for every FSM transition recorded on the aggregate.

    ``pre_commit_status`` is the status the order was in *before* the
    command handler made its mutations — captured by the caller right
    after fetching the aggregate. Walking the events in order, we use
    each event's target status as the next ``from_status``, so the
    chain is reconstructed even if the handler made multiple
    transitions in a single command (e.g. ``OrderEnteredHoldEvent``
    followed by ``OrderResumedFromHoldEvent`` — not currently used,
    but the algorithm is robust to it).

    Resume-from-hold (which produces ``OrderResumedFromHoldEvent``)
    targets the pre-hold status, so it is mapped from the event's
    payload field rather than the static table above.
    """
    if not order.domain_events:
        return
    cursor: OrderStatus | None = pre_commit_status
    for event in order.domain_events:
        target = _resolve_target_status(event, fallback=cursor)
        if target is None:
            continue  # informational event — skip
        await history_writer.append(
            order_id=order.id,
            from_status=cursor,
            to_status=target,
            event_type=event.event_type,
            event_id=event.event_id,
            actor=actor,
            metadata=_safe_metadata(event),
            occurred_at=event.occurred_at or datetime.now(UTC),
        )
        cursor = target


def _resolve_target_status(event, fallback: OrderStatus | None) -> OrderStatus | None:
    static = _FSM_EVENT_TO_STATUS.get(event.event_type)
    if static is not None:
        return static
    if event.event_type == "OrderResumedFromHoldEvent":
        raw = getattr(event, "resumed_to_status", "") or ""
        try:
            return OrderStatus(raw)
        except ValueError:
            return fallback
    return None


def _safe_metadata(event) -> dict | None:
    try:
        raw = asdict(event)
    except TypeError:
        return None
    cleaned: dict = {}
    for key, value in raw.items():
        if key in {"event_id", "occurred_at", "aggregate_type", "aggregate_id"}:
            continue
        cleaned[key] = _normalize(value)
    return cleaned or None


def _normalize(value):
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: _normalize(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_normalize(v) for v in value]
    return value
