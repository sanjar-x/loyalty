"""
Order aggregate — Loyality cross-border dropship FSM.

Reference: backend/docs/Order/Research - Order (2) State Machine FSM.md §15
+ Research - Order (6) Logistics Integration.md §16.

Order : Shipment = 1 : 2 minimum:
* Shipment #1 (cross-border, DobroPost CN→RU) created on `procure()`
* Shipment #2 (last-mile, russian carrier) created on `mark_arrived_in_ru()`
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import ClassVar

from attr import dataclass, field

from src.modules.order.domain.events import (
    OrderArrivedInRuEvent,
    OrderAwaitingPickupEvent,
    OrderCancelledEvent,
    OrderClosedEvent,
    OrderCreatedEvent,
    OrderDeliveredEvent,
    OrderEnteredHoldEvent,
    OrderEnteredLastMileEvent,
    OrderNotDeliveredEvent,
    OrderPaidEvent,
    OrderPickupPointChangedEvent,
    OrderProcuredEvent,
    OrderRefundedEvent,
    OrderResumedFromHoldEvent,
    OrderReturnedEvent,
    OrderReturningToWarehouseEvent,
    OrderReturnRequestedEvent,
)
from src.modules.order.domain.exceptions import (
    CancellationForbiddenError,
    OrderAlreadyTerminalError,
    OrderEmptyError,
    OrderHoldStateError,
    OrderInvalidTransitionError,
    OrderItemQuantityError,
    PickupPointChangeForbiddenError,
)
from src.modules.order.domain.recipient_snapshot import RecipientSnapshot
from src.modules.order.domain.value_objects import (
    PAID_STATUSES,
    TERMINAL_STATUSES,
    CancellationReason,
    HoldReason,
    IncomingDeclaration,
    OrderNumber,
    OrderStatus,
    PickupPointPreference,
    category_of,
)
from src.shared.domain.supplier_type import SupplierType
from src.shared.interfaces.entities import AggregateRoot
from src.shared.interfaces.fsm import StateMachineMixin

MAX_ITEM_QUANTITY = 99
HOLD_TTL_DAYS = 30
RETURN_WINDOW_DAYS = 14


@dataclass
class OrderItem:
    """Frozen snapshot of a SKU at order creation time.

    Carries shipment references that are populated incrementally as the
    cross-border (Shipment #1) and last-mile (Shipment #2) parcels are
    booked.
    """

    id: uuid.UUID
    sku_id: uuid.UUID
    product_id: uuid.UUID
    variant_id: uuid.UUID
    product_name: str
    variant_label: str | None
    supplier_type: SupplierType
    quantity: int
    unit_price_amount: int
    currency: str
    cross_border_shipment_id: uuid.UUID | None = None
    last_mile_shipment_id: uuid.UUID | None = None

    @property
    def line_total(self) -> int:
        return self.unit_price_amount * self.quantity


@dataclass
class Order(AggregateRoot, StateMachineMixin[OrderStatus]):
    """Loyality order aggregate (14-state FSM)."""

    # FSM contract -- consumed by ``StateMachineMixin._transition``.
    _TERMINAL_STATES: ClassVar[frozenset[OrderStatus]] = TERMINAL_STATUSES
    _invalid_transition_exc: ClassVar = OrderInvalidTransitionError
    _already_terminal_exc: ClassVar = OrderAlreadyTerminalError

    _ALLOWED_TRANSITIONS: ClassVar[dict[OrderStatus, set[OrderStatus]]] = {
        OrderStatus.PENDING: {
            OrderStatus.PAID,
            OrderStatus.CANCELLED,
        },
        OrderStatus.PAID: {
            OrderStatus.PROCURED,
            OrderStatus.CANCELLED,
        },
        OrderStatus.PROCURED: {
            OrderStatus.ARRIVED_IN_RU,
            OrderStatus.ON_HOLD,
            OrderStatus.CANCELLED,
        },
        OrderStatus.ON_HOLD: {
            OrderStatus.PROCURED,  # resume to where we came from
            OrderStatus.PAID,
            OrderStatus.ARRIVED_IN_RU,
            OrderStatus.IN_LAST_MILE,
            OrderStatus.CANCELLED,
        },
        OrderStatus.ARRIVED_IN_RU: {
            OrderStatus.IN_LAST_MILE,
            OrderStatus.ON_HOLD,
        },
        OrderStatus.IN_LAST_MILE: {
            OrderStatus.AWAITING_PICKUP,
            OrderStatus.RETURNING_TO_RU_WAREHOUSE,
            OrderStatus.ON_HOLD,
        },
        OrderStatus.AWAITING_PICKUP: {
            OrderStatus.DELIVERED,
            OrderStatus.RETURNING_TO_RU_WAREHOUSE,
        },
        OrderStatus.DELIVERED: {
            OrderStatus.CLOSED,
            OrderStatus.RETURN_IN_PROGRESS,
        },
        OrderStatus.RETURNING_TO_RU_WAREHOUSE: {
            OrderStatus.NOT_DELIVERED,
        },
        OrderStatus.RETURN_IN_PROGRESS: {
            OrderStatus.RETURNED,
        },
        OrderStatus.NOT_DELIVERED: set(),
        OrderStatus.RETURNED: set(),
        OrderStatus.CLOSED: set(),
        OrderStatus.CANCELLED: set(),
    }

    id: uuid.UUID
    identity_id: uuid.UUID
    cart_id: uuid.UUID
    status: OrderStatus
    total_amount: int
    currency: str
    cny_rate_at_checkout: Decimal | None
    pickup_point: PickupPointPreference
    recipient_snapshot: RecipientSnapshot
    payment_intent_id: uuid.UUID | None
    incoming_declaration: IncomingDeclaration | None
    procured_by_admin_id: uuid.UUID | None
    procured_at: datetime | None
    cross_border_shipment_id: uuid.UUID | None
    last_mile_shipment_id: uuid.UUID | None
    pre_hold_status: OrderStatus | None
    hold_reason: HoldReason | None
    hold_started_at: datetime | None
    hold_until: datetime | None
    cancellation_reason: CancellationReason | None
    created_at: datetime
    updated_at: datetime
    version: int
    items: list[OrderItem] = field(factory=list)

    # ---------------------------------------------------------------------------
    # TYPE-003 — guard ``status`` against direct mutation; FSM-managed
    # transitions go through ``StateMachineMixin._transition`` which uses
    # ``object.__setattr__`` to bypass this guard.
    # ---------------------------------------------------------------------------

    def __setattr__(self, name: str, value: object) -> None:
        if name == "status" and getattr(self, "_Order__initialized", False):
            raise AttributeError(
                "Cannot set 'status' directly on Order. "
                "Use the FSM transition methods (mark_paid / hold_order / "
                "cancel / etc.) instead."
            )
        super().__setattr__(name, value)

    def __attrs_post_init__(self) -> None:
        super().__attrs_post_init__()
        object.__setattr__(self, "_Order__initialized", True)

    # ---------------------------------------------------------------------------
    # Factory
    # ---------------------------------------------------------------------------

    @classmethod
    def create(
        cls,
        *,
        identity_id: uuid.UUID,
        cart_id: uuid.UUID,
        items: list[OrderItem],
        currency: str,
        pickup_point: PickupPointPreference,
        recipient_snapshot: RecipientSnapshot,
        cny_rate_at_checkout: Decimal | None = None,
    ) -> Order:
        if not items:
            raise OrderEmptyError()
        for itm in items:
            if itm.quantity < 1 or itm.quantity > MAX_ITEM_QUANTITY:
                raise OrderItemQuantityError(quantity=itm.quantity)
        total = sum(itm.line_total for itm in items)
        now = datetime.now(UTC)
        order = cls(
            id=uuid.uuid4(),
            identity_id=identity_id,
            cart_id=cart_id,
            status=OrderStatus.PENDING,
            total_amount=total,
            currency=currency,
            cny_rate_at_checkout=cny_rate_at_checkout,
            pickup_point=pickup_point,
            recipient_snapshot=recipient_snapshot,
            payment_intent_id=None,
            incoming_declaration=None,
            procured_by_admin_id=None,
            procured_at=None,
            cross_border_shipment_id=None,
            last_mile_shipment_id=None,
            pre_hold_status=None,
            hold_reason=None,
            hold_started_at=None,
            hold_until=None,
            cancellation_reason=None,
            created_at=now,
            updated_at=now,
            version=0,
            items=list(items),
        )
        order.add_domain_event(
            OrderCreatedEvent(
                order_id=order.id,
                identity_id=identity_id,
                cart_id=cart_id,
                total_amount=total,
                currency=currency,
                item_count=len(items),
            )
        )
        return order

    # ---------------------------------------------------------------------------
    # Helpers / projections
    # ---------------------------------------------------------------------------

    @property
    def number(self) -> OrderNumber:
        return OrderNumber.from_id(self.id, self.created_at)

    # ``is_terminal`` and ``_transition`` are now inherited from
    # ``StateMachineMixin`` (REFACT-001 PR-1b''). The mixin enforces
    # terminal-first then allowed-edge semantics with the same exception
    # classes (`OrderAlreadyTerminalError` / `OrderInvalidTransitionError`)
    # that the inlined version used.

    @property
    def was_paid(self) -> bool:
        return self.status in PAID_STATUSES

    # ---------------------------------------------------------------------------
    # FSM operations
    # ---------------------------------------------------------------------------

    def attach_payment_intent(self, payment_intent_id: uuid.UUID) -> None:
        """Bind a PaymentIntent without moving FSM (PENDING stays).

        FSM moves to PAID only on ``mark_paid`` after successful capture.
        """
        if self.status != OrderStatus.PENDING:
            raise OrderInvalidTransitionError(
                current=self.status.value, target="attach_payment_intent"
            )
        if self.payment_intent_id is not None:
            return  # idempotent — already attached
        self.payment_intent_id = payment_intent_id
        self.updated_at = datetime.now(UTC)

    def mark_paid(self, *, payment_intent_id: uuid.UUID) -> None:
        if self.status != OrderStatus.PENDING:
            raise OrderInvalidTransitionError(
                current=self.status.value, target=OrderStatus.PAID.value
            )
        if self.payment_intent_id is None:
            self.payment_intent_id = payment_intent_id
        elif self.payment_intent_id != payment_intent_id:
            raise OrderInvalidTransitionError(
                current=self.status.value, target=OrderStatus.PAID.value
            )
        self._transition(OrderStatus.PAID)
        self.add_domain_event(
            OrderPaidEvent(
                order_id=self.id,
                payment_intent_id=payment_intent_id,
                paid_amount=self.total_amount,
                currency=self.currency,
            )
        )

    def procure(
        self,
        *,
        incoming_declaration: IncomingDeclaration,
        admin_id: uuid.UUID,
    ) -> None:
        """Manager has purchased the goods on the Chinese marketplace and
        attached the Chinese tracking number. Triggers DobroPost shipment.
        """
        self._transition(OrderStatus.PROCURED)
        self.incoming_declaration = incoming_declaration
        self.procured_by_admin_id = admin_id
        self.procured_at = datetime.now(UTC)
        self.add_domain_event(
            OrderProcuredEvent(
                order_id=self.id,
                incoming_declaration=incoming_declaration.value,
                procured_by_admin_id=admin_id,
            )
        )

    def attach_cross_border_shipment(self, shipment_id: uuid.UUID) -> None:
        """Persist DobroPost shipment id after the gateway booked it."""
        self.cross_border_shipment_id = shipment_id
        for item in self.items:
            if item.cross_border_shipment_id is None:
                item.cross_border_shipment_id = shipment_id
        self.updated_at = datetime.now(UTC)

    def mark_arrived_in_ru(self) -> None:
        self._transition(OrderStatus.ARRIVED_IN_RU)
        self.add_domain_event(
            OrderArrivedInRuEvent(
                order_id=self.id,
                cross_border_shipment_id=self.cross_border_shipment_id,
            )
        )

    def attach_last_mile_shipment(self, shipment_id: uuid.UUID) -> None:
        self.last_mile_shipment_id = shipment_id
        for item in self.items:
            if item.last_mile_shipment_id is None:
                item.last_mile_shipment_id = shipment_id
        self.updated_at = datetime.now(UTC)

    def mark_in_last_mile(self) -> None:
        self._transition(OrderStatus.IN_LAST_MILE)
        self.add_domain_event(
            OrderEnteredLastMileEvent(
                order_id=self.id,
                last_mile_shipment_id=self.last_mile_shipment_id,
            )
        )

    def mark_awaiting_pickup(self) -> None:
        self._transition(OrderStatus.AWAITING_PICKUP)
        self.add_domain_event(OrderAwaitingPickupEvent(order_id=self.id))

    def mark_delivered(self) -> None:
        self._transition(OrderStatus.DELIVERED)
        self.add_domain_event(OrderDeliveredEvent(order_id=self.id))

    def close(self) -> None:
        """DELIVERED → CLOSED after 14-day return window."""
        if self.status != OrderStatus.DELIVERED:
            raise OrderInvalidTransitionError(
                current=self.status.value, target=OrderStatus.CLOSED.value
            )
        if self.updated_at + timedelta(days=RETURN_WINDOW_DAYS) > datetime.now(UTC):
            raise OrderInvalidTransitionError(
                current=self.status.value, target="close (return window not elapsed)"
            )
        self._transition(OrderStatus.CLOSED)
        self.add_domain_event(OrderClosedEvent(order_id=self.id))

    # ---------------------------------------------------------------------------
    # Hold / resume — semantic lock (research (2) §15.5)
    # ---------------------------------------------------------------------------

    _HOLDABLE: ClassVar[set[OrderStatus]] = {
        OrderStatus.PAID,
        OrderStatus.PROCURED,
        OrderStatus.ARRIVED_IN_RU,
        OrderStatus.IN_LAST_MILE,
    }

    def hold(self, *, reason: HoldReason) -> None:
        if self.status == OrderStatus.ON_HOLD:
            return  # idempotent
        if self.status not in self._HOLDABLE:
            raise OrderHoldStateError(status=self.status.value)
        self.pre_hold_status = self.status
        self.hold_reason = reason
        now = datetime.now(UTC)
        self.hold_started_at = now
        self.hold_until = now + timedelta(days=HOLD_TTL_DAYS)
        self._transition(OrderStatus.ON_HOLD)
        self.add_domain_event(
            OrderEnteredHoldEvent(
                order_id=self.id,
                reason=reason.value,
                pre_hold_status=(
                    self.pre_hold_status.value if self.pre_hold_status else ""
                ),
                hold_until=self.hold_until.isoformat(),
            )
        )

    def resume_from_hold(self) -> None:
        if self.status != OrderStatus.ON_HOLD or self.pre_hold_status is None:
            raise OrderHoldStateError(status=self.status.value)
        target = self.pre_hold_status
        self._transition(target)
        self.add_domain_event(
            OrderResumedFromHoldEvent(order_id=self.id, resumed_to_status=target.value)
        )
        self.pre_hold_status = None
        self.hold_reason = None
        self.hold_started_at = None
        self.hold_until = None

    def is_hold_ttl_expired(self) -> bool:
        if self.status != OrderStatus.ON_HOLD or self.hold_until is None:
            return False
        return datetime.now(UTC) >= self.hold_until

    # ---------------------------------------------------------------------------
    # Returning to warehouse / not delivered
    # ---------------------------------------------------------------------------

    def mark_returning_to_warehouse(self, *, reason: str = "") -> None:
        if self.status not in {
            OrderStatus.IN_LAST_MILE,
            OrderStatus.AWAITING_PICKUP,
        }:
            raise OrderInvalidTransitionError(
                current=self.status.value,
                target=OrderStatus.RETURNING_TO_RU_WAREHOUSE.value,
            )
        self._transition(OrderStatus.RETURNING_TO_RU_WAREHOUSE)
        self.add_domain_event(
            OrderReturningToWarehouseEvent(order_id=self.id, reason=reason)
        )

    def mark_not_delivered(self) -> None:
        self._transition(OrderStatus.NOT_DELIVERED)
        self.add_domain_event(OrderNotDeliveredEvent(order_id=self.id))

    def request_return(self, *, reason: str = "") -> None:
        self._transition(OrderStatus.RETURN_IN_PROGRESS)
        self.add_domain_event(
            OrderReturnRequestedEvent(order_id=self.id, reason=reason)
        )

    def mark_returned(self) -> None:
        self._transition(OrderStatus.RETURNED)
        self.add_domain_event(OrderReturnedEvent(order_id=self.id))

    # ---------------------------------------------------------------------------
    # Cancel / refund
    # ---------------------------------------------------------------------------

    _CANCELLABLE: ClassVar[set[OrderStatus]] = {
        OrderStatus.PENDING,
        OrderStatus.PAID,
        OrderStatus.PROCURED,
        OrderStatus.ON_HOLD,
    }

    def cancel(self, *, reason: CancellationReason, actor_id: str = "") -> bool:
        """Cancel the order. Pre-payment → CANCELLED; post-payment → CANCELLED
        with refund event flagged. Forward-going compensation per research (7) §9.

        After ``ARRIVED_IN_RU`` cancellation is forbidden — use return flow.

        Returns True if a refund must be issued externally.
        """
        if self.is_terminal:
            raise OrderAlreadyTerminalError(status=self.status.value)
        if self.status not in self._CANCELLABLE:
            raise CancellationForbiddenError(status=self.status.value)
        refund_required = self.was_paid
        category = category_of(reason)
        self._transition(OrderStatus.CANCELLED)
        self.cancellation_reason = reason
        self.add_domain_event(
            OrderCancelledEvent(
                order_id=self.id,
                reason_category=category.value,
                reason_code=reason.value,
                initiated_by=category.value,
                actor_id=actor_id,
                refund_required=refund_required,
            )
        )
        if refund_required:
            self.add_domain_event(
                OrderRefundedEvent(
                    order_id=self.id,
                    refund_amount=self.total_amount,
                    currency=self.currency,
                )
            )
        return refund_required

    # ---------------------------------------------------------------------------
    # Pickup point change (allowed before last-mile is created)
    # ---------------------------------------------------------------------------

    _PICKUP_CHANGE_ALLOWED: ClassVar[set[OrderStatus]] = {
        OrderStatus.PENDING,
        OrderStatus.PAID,
        OrderStatus.PROCURED,
        OrderStatus.ARRIVED_IN_RU,
    }

    # ---------------------------------------------------------------------------
    # Recipient snapshot refresh (used after PASSPORT_INVALID hold)
    # ---------------------------------------------------------------------------

    def refresh_recipient_snapshot(self, fresh: RecipientSnapshot) -> None:
        """Replace the recipient snapshot with a freshly captured copy.

        Used by the customer / manager after correcting passport details
        on the underlying Recipient — the order can then be resumed from
        ON_HOLD via ``resume_from_hold`` once DobroPost re-validates.

        Refresh is allowed only when the order is in ON_HOLD with
        reason=PASSPORT_INVALID (the only state where stale customs data
        is the actual blocker).
        """
        if (
            self.status != OrderStatus.ON_HOLD
            or self.hold_reason is not HoldReason.PASSPORT_INVALID
        ):
            raise OrderHoldStateError(status=self.status.value)
        self.recipient_snapshot = self.recipient_snapshot.with_updated_data(fresh=fresh)
        self.updated_at = datetime.now(UTC)

    def change_pickup_point(self, new: PickupPointPreference) -> None:
        if self.status not in self._PICKUP_CHANGE_ALLOWED:
            raise PickupPointChangeForbiddenError(status=self.status.value)
        if (
            self.pickup_point.carrier == new.carrier
            and self.pickup_point.point_id == new.point_id
        ):
            return
        self.pickup_point = new
        self.updated_at = datetime.now(UTC)
        self.add_domain_event(
            OrderPickupPointChangedEvent(
                order_id=self.id,
                new_carrier=new.carrier.value,
                new_point_id=new.point_id,
            )
        )
