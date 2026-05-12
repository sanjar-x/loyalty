"""Order domain events — Loyality FSM."""

import uuid
from dataclasses import dataclass

from src.shared.interfaces.entities import ModuleDomainEvent


@dataclass(frozen=True)
class OrderEvent(ModuleDomainEvent, abstract=True):
    """Intermediate base for all order-domain events."""

    aggregate_type: str = "order"


@dataclass(frozen=True)
class OrderCreatedEvent(
    OrderEvent,
    required_fields=("order_id", "identity_id"),
    aggregate_id_field="order_id",
):
    order_id: uuid.UUID | None = None
    identity_id: uuid.UUID | None = None
    cart_id: uuid.UUID | None = None
    total_amount: int = 0
    currency: str = ""
    item_count: int = 0
    event_type: str = "OrderCreatedEvent"


@dataclass(frozen=True)
class OrderPaidEvent(
    OrderEvent,
    required_fields=("order_id", "payment_intent_id"),
    aggregate_id_field="order_id",
):
    order_id: uuid.UUID | None = None
    payment_intent_id: uuid.UUID | None = None
    paid_amount: int = 0
    currency: str = ""
    event_type: str = "OrderPaidEvent"


@dataclass(frozen=True)
class OrderProcuredEvent(
    OrderEvent,
    required_fields=("order_id", "incoming_declaration"),
    aggregate_id_field="order_id",
):
    order_id: uuid.UUID | None = None
    incoming_declaration: str = ""
    procured_by_admin_id: uuid.UUID | None = None
    event_type: str = "OrderProcuredEvent"


@dataclass(frozen=True)
class OrderArrivedInRuEvent(
    OrderEvent,
    required_fields=("order_id",),
    aggregate_id_field="order_id",
):
    order_id: uuid.UUID | None = None
    cross_border_shipment_id: uuid.UUID | None = None
    event_type: str = "OrderArrivedInRuEvent"


@dataclass(frozen=True)
class OrderEnteredLastMileEvent(
    OrderEvent,
    required_fields=("order_id",),
    aggregate_id_field="order_id",
):
    order_id: uuid.UUID | None = None
    last_mile_shipment_id: uuid.UUID | None = None
    event_type: str = "OrderEnteredLastMileEvent"


@dataclass(frozen=True)
class OrderAwaitingPickupEvent(
    OrderEvent,
    required_fields=("order_id",),
    aggregate_id_field="order_id",
):
    order_id: uuid.UUID | None = None
    event_type: str = "OrderAwaitingPickupEvent"


@dataclass(frozen=True)
class OrderDeliveredEvent(
    OrderEvent,
    required_fields=("order_id",),
    aggregate_id_field="order_id",
):
    order_id: uuid.UUID | None = None
    event_type: str = "OrderDeliveredEvent"


@dataclass(frozen=True)
class OrderClosedEvent(
    OrderEvent,
    required_fields=("order_id",),
    aggregate_id_field="order_id",
):
    order_id: uuid.UUID | None = None
    event_type: str = "OrderClosedEvent"


@dataclass(frozen=True)
class OrderEnteredHoldEvent(
    OrderEvent,
    required_fields=("order_id",),
    aggregate_id_field="order_id",
):
    order_id: uuid.UUID | None = None
    reason: str = ""
    pre_hold_status: str = ""
    hold_until: str = ""
    event_type: str = "OrderEnteredHoldEvent"


@dataclass(frozen=True)
class OrderResumedFromHoldEvent(
    OrderEvent,
    required_fields=("order_id",),
    aggregate_id_field="order_id",
):
    order_id: uuid.UUID | None = None
    resumed_to_status: str = ""
    event_type: str = "OrderResumedFromHoldEvent"


@dataclass(frozen=True)
class OrderReturningToWarehouseEvent(
    OrderEvent,
    required_fields=("order_id",),
    aggregate_id_field="order_id",
):
    order_id: uuid.UUID | None = None
    reason: str = ""
    event_type: str = "OrderReturningToWarehouseEvent"


@dataclass(frozen=True)
class OrderNotDeliveredEvent(
    OrderEvent,
    required_fields=("order_id",),
    aggregate_id_field="order_id",
):
    order_id: uuid.UUID | None = None
    event_type: str = "OrderNotDeliveredEvent"


@dataclass(frozen=True)
class OrderReturnRequestedEvent(
    OrderEvent,
    required_fields=("order_id",),
    aggregate_id_field="order_id",
):
    order_id: uuid.UUID | None = None
    reason: str = ""
    event_type: str = "OrderReturnRequestedEvent"


@dataclass(frozen=True)
class OrderReturnedEvent(
    OrderEvent,
    required_fields=("order_id",),
    aggregate_id_field="order_id",
):
    order_id: uuid.UUID | None = None
    event_type: str = "OrderReturnedEvent"


@dataclass(frozen=True)
class OrderCancelledEvent(
    OrderEvent,
    required_fields=("order_id",),
    aggregate_id_field="order_id",
):
    order_id: uuid.UUID | None = None
    reason_category: str = ""
    reason_code: str = ""
    initiated_by: str = ""
    actor_id: str = ""
    refund_required: bool = False
    event_type: str = "OrderCancelledEvent"


@dataclass(frozen=True)
class OrderRefundedEvent(
    OrderEvent,
    required_fields=("order_id",),
    aggregate_id_field="order_id",
):
    order_id: uuid.UUID | None = None
    refund_amount: int = 0
    currency: str = ""
    event_type: str = "OrderRefundedEvent"


@dataclass(frozen=True)
class OrderPickupPointChangedEvent(
    OrderEvent,
    required_fields=("order_id",),
    aggregate_id_field="order_id",
):
    order_id: uuid.UUID | None = None
    new_carrier: str = ""
    new_point_id: str = ""
    event_type: str = "OrderPickupPointChangedEvent"
