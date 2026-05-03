"""Unit tests for the Loyality Order FSM (14 states).

Reference: backend/docs/Order/Research - Order (2) State Machine FSM.md §15.
"""

import uuid
from datetime import UTC, date, datetime, timedelta

import pytest

from src.modules.order.domain.entities import (
    HOLD_TTL_DAYS,
    Order,
    OrderItem,
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
    CancellationReason,
    HoldReason,
    IncomingDeclaration,
    OrderStatus,
    PickupCarrier,
    PickupPointPreference,
)

pytestmark = pytest.mark.unit


def _item(quantity: int = 1, price: int = 10000) -> OrderItem:
    return OrderItem(
        id=uuid.uuid4(),
        sku_id=uuid.uuid4(),
        product_id=uuid.uuid4(),
        variant_id=uuid.uuid4(),
        product_name="Sneakers",
        variant_label="42",
        supplier_type="cross_border",
        quantity=quantity,
        unit_price_amount=price,
        currency="RUB",
    )


def _pickup() -> PickupPointPreference:
    return PickupPointPreference(carrier=PickupCarrier.CDEK, point_id="MSK-1")


def _recipient_snapshot() -> RecipientSnapshot:
    return RecipientSnapshot(
        recipient_id=str(uuid.uuid4()),
        full_name_ru="Иван Иванов",
        full_name_lat="Ivan Ivanov",
        phone="+79108897762",
        email="ivan@example.com",
        passport_serial="1234",
        passport_number="567890",
        passport_issue_date=date(2015, 5, 22),
        birth_date=date(1990, 1, 1),
        inn="500100732272",
    )


def _order(items: list[OrderItem] | None = None) -> Order:
    return Order.create(
        identity_id=uuid.uuid4(),
        cart_id=uuid.uuid4(),
        items=items or [_item()],
        currency="RUB",
        pickup_point=_pickup(),
        recipient_snapshot=_recipient_snapshot(),
    )


def _drive_to_paid(order: Order) -> uuid.UUID:
    intent_id = uuid.uuid4()
    order.attach_payment_intent(intent_id)
    order.mark_paid(payment_intent_id=intent_id)
    return intent_id


def _drive_to_procured(order: Order) -> None:
    _drive_to_paid(order)
    order.procure(
        incoming_declaration=IncomingDeclaration.parse("CN-12345"),
        admin_id=uuid.uuid4(),
    )


def _drive_to_arrived_in_ru(order: Order) -> None:
    _drive_to_procured(order)
    order.attach_cross_border_shipment(uuid.uuid4())
    order.mark_arrived_in_ru()


def _drive_to_in_last_mile(order: Order) -> None:
    _drive_to_arrived_in_ru(order)
    order.attach_last_mile_shipment(uuid.uuid4())
    order.mark_in_last_mile()


def _drive_to_awaiting_pickup(order: Order) -> None:
    _drive_to_in_last_mile(order)
    order.mark_awaiting_pickup()


def _drive_to_delivered(order: Order) -> None:
    _drive_to_awaiting_pickup(order)
    order.mark_delivered()


# ---------------------------------------------------------------------------
# Create / item validation
# ---------------------------------------------------------------------------


class TestCreate:
    def test_empty_order_rejected(self) -> None:
        with pytest.raises(OrderEmptyError):
            Order.create(
                identity_id=uuid.uuid4(),
                cart_id=uuid.uuid4(),
                items=[],
                currency="RUB",
                pickup_point=_pickup(),
                recipient_snapshot=_recipient_snapshot(),
            )

    def test_invalid_quantity_rejected(self) -> None:
        with pytest.raises(OrderItemQuantityError):
            _order([_item(quantity=0)])
        with pytest.raises(OrderItemQuantityError):
            _order([_item(quantity=100)])

    def test_emits_created_event(self) -> None:
        order = _order()
        assert any(ev.event_type == "OrderCreatedEvent" for ev in order.domain_events)
        assert order.status == OrderStatus.PENDING


# ---------------------------------------------------------------------------
# Happy path through full lifecycle
# ---------------------------------------------------------------------------


class TestHappyPath:
    def test_full_lifecycle(self) -> None:
        order = _order()
        intent_id = uuid.uuid4()

        order.attach_payment_intent(intent_id)
        assert order.status == OrderStatus.PENDING  # auth-only doesn't move FSM

        order.mark_paid(payment_intent_id=intent_id)
        assert order.status == OrderStatus.PAID

        order.procure(
            incoming_declaration=IncomingDeclaration.parse("CN-XYZ123"),
            admin_id=uuid.uuid4(),
        )
        assert order.status == OrderStatus.PROCURED
        assert order.incoming_declaration is not None
        assert order.incoming_declaration.value == "CN-XYZ123"
        assert order.procured_at is not None

        order.attach_cross_border_shipment(uuid.uuid4())
        order.mark_arrived_in_ru()
        assert order.status == OrderStatus.ARRIVED_IN_RU

        order.attach_last_mile_shipment(uuid.uuid4())
        order.mark_in_last_mile()
        assert order.status == OrderStatus.IN_LAST_MILE

        order.mark_awaiting_pickup()
        assert order.status == OrderStatus.AWAITING_PICKUP

        order.mark_delivered()
        assert order.status == OrderStatus.DELIVERED

        # Force return-window expiry then close.
        order.updated_at = datetime.now(UTC) - timedelta(days=15)
        order.close()
        assert order.status == OrderStatus.CLOSED
        assert order.is_terminal


# ---------------------------------------------------------------------------
# Hold / resume — semantic lock
# ---------------------------------------------------------------------------


class TestHoldResume:
    def test_hold_and_resume(self) -> None:
        order = _order()
        _drive_to_procured(order)
        order.hold(reason=HoldReason.PASSPORT_INVALID)
        assert order.status == OrderStatus.ON_HOLD
        assert order.hold_reason == HoldReason.PASSPORT_INVALID
        assert order.pre_hold_status == OrderStatus.PROCURED
        assert order.hold_until is not None

        order.resume_from_hold()
        assert order.status == OrderStatus.PROCURED
        assert order.hold_reason is None
        assert order.pre_hold_status is None

    def test_hold_idempotent(self) -> None:
        order = _order()
        _drive_to_procured(order)
        order.hold(reason=HoldReason.STUCK_IN_CN)
        first_until = order.hold_until
        order.hold(reason=HoldReason.STUCK_IN_CN)  # no-op
        assert order.status == OrderStatus.ON_HOLD
        assert order.hold_until == first_until

    def test_hold_pending_rejected(self) -> None:
        order = _order()
        with pytest.raises(OrderHoldStateError):
            order.hold(reason=HoldReason.MANUAL_REVIEW)

    def test_resume_without_hold_rejected(self) -> None:
        order = _order()
        with pytest.raises(OrderHoldStateError):
            order.resume_from_hold()

    def test_hold_ttl(self) -> None:
        order = _order()
        _drive_to_procured(order)
        order.hold(reason=HoldReason.STUCK_IN_CN)
        assert order.is_hold_ttl_expired() is False
        order.hold_until = datetime.now(UTC) - timedelta(seconds=1)
        assert order.is_hold_ttl_expired() is True


# ---------------------------------------------------------------------------
# Cancel / refund (taxonomy)
# ---------------------------------------------------------------------------


class TestCancel:
    def test_cancel_pending_no_refund(self) -> None:
        order = _order()
        refund = order.cancel(
            reason=CancellationReason.CUSTOMER_CHANGED_MIND, actor_id="u-1"
        )
        assert order.status == OrderStatus.CANCELLED
        assert refund is False

    def test_cancel_paid_refund_required(self) -> None:
        order = _order()
        _drive_to_paid(order)
        refund = order.cancel(
            reason=CancellationReason.MERCHANT_OUT_OF_STOCK, actor_id="m-1"
        )
        assert order.status == OrderStatus.CANCELLED
        assert refund is True
        assert any(ev.event_type == "OrderRefundedEvent" for ev in order.domain_events)

    def test_cancel_after_arrived_forbidden(self) -> None:
        order = _order()
        _drive_to_arrived_in_ru(order)
        with pytest.raises(CancellationForbiddenError):
            order.cancel(
                reason=CancellationReason.CUSTOMER_CHANGED_MIND,
                actor_id="u-1",
            )

    def test_cancel_terminal_rejected(self) -> None:
        order = _order()
        order.cancel(reason=CancellationReason.CUSTOMER_CHANGED_MIND, actor_id="u-1")
        with pytest.raises(OrderAlreadyTerminalError):
            order.cancel(
                reason=CancellationReason.CUSTOMER_CHANGED_MIND,
                actor_id="u-1",
            )


# ---------------------------------------------------------------------------
# Pickup point change
# ---------------------------------------------------------------------------


class TestPickupPoint:
    def test_change_allowed_before_last_mile(self) -> None:
        order = _order()
        _drive_to_arrived_in_ru(order)
        order.change_pickup_point(
            PickupPointPreference(carrier=PickupCarrier.YANDEX, point_id="YDX-7")
        )
        assert order.pickup_point.carrier == PickupCarrier.YANDEX

    def test_change_forbidden_after_last_mile(self) -> None:
        order = _order()
        _drive_to_in_last_mile(order)
        with pytest.raises(PickupPointChangeForbiddenError):
            order.change_pickup_point(
                PickupPointPreference(carrier=PickupCarrier.POCHTA, point_id="POST-1")
            )


# ---------------------------------------------------------------------------
# Illegal transitions matrix
# ---------------------------------------------------------------------------


class TestIllegalTransitions:
    def test_pending_cant_procure(self) -> None:
        order = _order()
        with pytest.raises(OrderInvalidTransitionError):
            order.procure(
                incoming_declaration=IncomingDeclaration.parse("CN-1"),
                admin_id=uuid.uuid4(),
            )

    def test_pending_cant_close(self) -> None:
        order = _order()
        with pytest.raises(OrderInvalidTransitionError):
            order.close()

    def test_close_before_window(self) -> None:
        order = _order()
        _drive_to_delivered(order)
        with pytest.raises(OrderInvalidTransitionError):
            order.close()

    def test_paid_cant_skip_to_in_last_mile(self) -> None:
        order = _order()
        _drive_to_paid(order)
        with pytest.raises(OrderInvalidTransitionError):
            order.mark_in_last_mile()


# ---------------------------------------------------------------------------
# Customer-facing status mapper
# ---------------------------------------------------------------------------


class TestCustomerFacing:
    def test_mapping_covers_every_status(self) -> None:
        from src.modules.order.domain.value_objects import to_customer_facing

        for status in OrderStatus:
            # must not raise
            to_customer_facing(status)


# ---------------------------------------------------------------------------
# Incoming declaration parser
# ---------------------------------------------------------------------------


class TestIncomingDeclaration:
    def test_too_long(self) -> None:
        with pytest.raises(ValueError):
            IncomingDeclaration.parse("X" * 16)

    def test_empty(self) -> None:
        with pytest.raises(ValueError):
            IncomingDeclaration.parse("")

    def test_invalid_chars(self) -> None:
        with pytest.raises(ValueError):
            IncomingDeclaration.parse("CN 123")  # space

    def test_normal(self) -> None:
        d = IncomingDeclaration.parse("CN-ABC-123")
        assert d.value == "CN-ABC-123"


# ---------------------------------------------------------------------------
# Hold TTL constant
# ---------------------------------------------------------------------------


def test_hold_ttl_constant_30_days() -> None:
    assert HOLD_TTL_DAYS == 30
