"""Order domain events — Loyality FSM."""

import uuid
from dataclasses import dataclass
from typing import ClassVar

from src.shared.interfaces.entities import DomainEvent


@dataclass
class OrderEvent(DomainEvent):
    _required_fields: ClassVar[tuple[str, ...]] = ()
    _aggregate_id_field: ClassVar[str] = ""

    aggregate_type: str = "order"
    event_type: str = "OrderEvent"

    def __init_subclass__(
        cls,
        *,
        required_fields: tuple[str, ...] | None = None,
        aggregate_id_field: str | None = None,
        **kwargs: object,
    ) -> None:
        super().__init_subclass__(**kwargs)
        if required_fields is not None:
            cls._required_fields = required_fields
        if aggregate_id_field is not None:
            cls._aggregate_id_field = aggregate_id_field
        if required_fields is not None and cls.event_type == "OrderEvent":
            raise TypeError(
                f"{cls.__name__} must define its own 'event_type' "
                "(inherited 'OrderEvent' would misroute events)"
            )

    def __post_init__(self) -> None:
        cls_name = type(self).__name__
        for field_name in self._required_fields:
            if getattr(self, field_name) is None:
                raise ValueError(f"{field_name} is required for {cls_name}")
        if not self.aggregate_id and self._aggregate_id_field:
            self.aggregate_id = str(getattr(self, self._aggregate_id_field))


@dataclass
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


@dataclass
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


@dataclass
class OrderProcuredEvent(
    OrderEvent,
    required_fields=("order_id", "incoming_declaration"),
    aggregate_id_field="order_id",
):
    order_id: uuid.UUID | None = None
    incoming_declaration: str = ""
    procured_by_admin_id: uuid.UUID | None = None
    event_type: str = "OrderProcuredEvent"


@dataclass
class OrderArrivedInRuEvent(
    OrderEvent,
    required_fields=("order_id",),
    aggregate_id_field="order_id",
):
    order_id: uuid.UUID | None = None
    cross_border_shipment_id: uuid.UUID | None = None
    event_type: str = "OrderArrivedInRuEvent"


@dataclass
class OrderEnteredLastMileEvent(
    OrderEvent,
    required_fields=("order_id",),
    aggregate_id_field="order_id",
):
    order_id: uuid.UUID | None = None
    last_mile_shipment_id: uuid.UUID | None = None
    event_type: str = "OrderEnteredLastMileEvent"


@dataclass
class OrderAwaitingPickupEvent(
    OrderEvent,
    required_fields=("order_id",),
    aggregate_id_field="order_id",
):
    order_id: uuid.UUID | None = None
    event_type: str = "OrderAwaitingPickupEvent"


@dataclass
class OrderDeliveredEvent(
    OrderEvent,
    required_fields=("order_id",),
    aggregate_id_field="order_id",
):
    order_id: uuid.UUID | None = None
    event_type: str = "OrderDeliveredEvent"


@dataclass
class OrderClosedEvent(
    OrderEvent,
    required_fields=("order_id",),
    aggregate_id_field="order_id",
):
    order_id: uuid.UUID | None = None
    event_type: str = "OrderClosedEvent"


@dataclass
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


@dataclass
class OrderResumedFromHoldEvent(
    OrderEvent,
    required_fields=("order_id",),
    aggregate_id_field="order_id",
):
    order_id: uuid.UUID | None = None
    resumed_to_status: str = ""
    event_type: str = "OrderResumedFromHoldEvent"


@dataclass
class OrderReturningToWarehouseEvent(
    OrderEvent,
    required_fields=("order_id",),
    aggregate_id_field="order_id",
):
    order_id: uuid.UUID | None = None
    reason: str = ""
    event_type: str = "OrderReturningToWarehouseEvent"


@dataclass
class OrderNotDeliveredEvent(
    OrderEvent,
    required_fields=("order_id",),
    aggregate_id_field="order_id",
):
    order_id: uuid.UUID | None = None
    event_type: str = "OrderNotDeliveredEvent"


@dataclass
class OrderReturnRequestedEvent(
    OrderEvent,
    required_fields=("order_id",),
    aggregate_id_field="order_id",
):
    order_id: uuid.UUID | None = None
    reason: str = ""
    event_type: str = "OrderReturnRequestedEvent"


@dataclass
class OrderReturnedEvent(
    OrderEvent,
    required_fields=("order_id",),
    aggregate_id_field="order_id",
):
    order_id: uuid.UUID | None = None
    event_type: str = "OrderReturnedEvent"


@dataclass
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


@dataclass
class OrderRefundedEvent(
    OrderEvent,
    required_fields=("order_id",),
    aggregate_id_field="order_id",
):
    order_id: uuid.UUID | None = None
    refund_amount: int = 0
    currency: str = ""
    event_type: str = "OrderRefundedEvent"


@dataclass
class OrderPickupPointChangedEvent(
    OrderEvent,
    required_fields=("order_id",),
    aggregate_id_field="order_id",
):
    order_id: uuid.UUID | None = None
    new_carrier: str = ""
    new_point_id: str = ""
    event_type: str = "OrderPickupPointChangedEvent"
