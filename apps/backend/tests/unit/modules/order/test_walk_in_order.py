"""Unit tests for the walk-in (admin-created offline) Order flow.

Covers:
* ``Order.create_walk_in`` factory invariants (is_walk_in=True, phantom
  cart_id, OrderCreatedEvent emitted, empty/qty validation).
* ``Order.mark_paid_offline`` FSM transition + non-walk-in guard +
  PENDING-only constraint + OrderPaidOfflineEvent payload.
* ``OfflinePaymentReceipt`` reference-required invariant.
* ``Order.refresh_recipient_snapshot`` guard for walk-in orders.
"""

import uuid
from datetime import UTC, date, datetime

import pytest

from src.modules.order.domain.entities import Order, OrderItem
from src.modules.order.domain.events import (
    OrderCreatedEvent,
    OrderPaidOfflineEvent,
)
from src.modules.order.domain.exceptions import (
    OrderEmptyError,
    OrderInvalidTransitionError,
    OrderItemQuantityError,
    WalkInRefreshRecipientForbiddenError,
)
from src.modules.order.domain.recipient_snapshot import RecipientSnapshot
from src.modules.order.domain.value_objects import (
    HoldReason,
    IncomingDeclaration,
    OfflinePaymentMethod,
    OfflinePaymentReceipt,
    OrderStatus,
    PickupCarrier,
    PickupPointPreference,
)
from src.shared.domain.supplier_type import SupplierType

pytestmark = pytest.mark.unit


def _item(quantity: int = 1, price: int = 10000) -> OrderItem:
    return OrderItem(
        id=uuid.uuid4(),
        sku_id=uuid.uuid4(),
        product_id=uuid.uuid4(),
        variant_id=uuid.uuid4(),
        product_name="Sneakers",
        variant_label="42",
        supplier_type=SupplierType.LOCAL,
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


def _receipt() -> OfflinePaymentReceipt:
    return OfflinePaymentReceipt(
        method=OfflinePaymentMethod.CASH,
        reference="POS-12345",
        paid_at=datetime.now(UTC),
    )


def _walk_in_order(items: list[OrderItem] | None = None) -> Order:
    return Order.create_walk_in(
        identity_id=uuid.uuid4(),
        items=items or [_item()],
        currency="RUB",
        pickup_point=_pickup(),
        recipient_snapshot=_recipient_snapshot(),
    )


# ---------------------------------------------------------------------------
# OfflinePaymentReceipt
# ---------------------------------------------------------------------------


class TestOfflinePaymentReceipt:
    def test_empty_reference_rejected(self) -> None:
        with pytest.raises(ValueError, match="reference must be non-empty"):
            OfflinePaymentReceipt(
                method=OfflinePaymentMethod.CASH,
                reference="   ",
                paid_at=datetime.now(UTC),
            )

    def test_valid_receipt_constructs(self) -> None:
        receipt = OfflinePaymentReceipt(
            method=OfflinePaymentMethod.BANK_TRANSFER,
            reference="TX-0001",
            paid_at=datetime(2026, 5, 16, 12, tzinfo=UTC),
        )
        assert receipt.method is OfflinePaymentMethod.BANK_TRANSFER
        assert receipt.reference == "TX-0001"


# ---------------------------------------------------------------------------
# Order.create_walk_in
# ---------------------------------------------------------------------------


class TestCreateWalkIn:
    def test_walk_in_flag_set(self) -> None:
        order = _walk_in_order()
        assert order.is_walk_in is True
        assert order.status is OrderStatus.PENDING

    def test_phantom_cart_id_is_generated(self) -> None:
        order = _walk_in_order()
        assert isinstance(order.cart_id, uuid.UUID)

    def test_no_payment_intent_at_birth(self) -> None:
        order = _walk_in_order()
        assert order.payment_intent_id is None

    def test_total_amount_includes_delivery(self) -> None:
        order = Order.create_walk_in(
            identity_id=uuid.uuid4(),
            items=[_item(quantity=2, price=5000)],
            currency="RUB",
            pickup_point=_pickup(),
            recipient_snapshot=_recipient_snapshot(),
            delivery_amount=300,
        )
        assert order.total_amount == 10300
        assert order.items_total == 10000
        assert order.delivery_amount == 300

    def test_empty_items_rejected(self) -> None:
        with pytest.raises(OrderEmptyError):
            Order.create_walk_in(
                identity_id=uuid.uuid4(),
                items=[],
                currency="RUB",
                pickup_point=_pickup(),
                recipient_snapshot=_recipient_snapshot(),
            )

    def test_invalid_quantity_rejected(self) -> None:
        with pytest.raises(OrderItemQuantityError):
            Order.create_walk_in(
                identity_id=uuid.uuid4(),
                items=[_item(quantity=0)],
                currency="RUB",
                pickup_point=_pickup(),
                recipient_snapshot=_recipient_snapshot(),
            )

    def test_emits_order_created_event(self) -> None:
        order = _walk_in_order()
        events = order.domain_events
        assert any(isinstance(e, OrderCreatedEvent) for e in events)
        created = next(e for e in events if isinstance(e, OrderCreatedEvent))
        assert created.order_id == order.id
        assert created.identity_id == order.identity_id


# ---------------------------------------------------------------------------
# Order.mark_paid_offline
# ---------------------------------------------------------------------------


class TestMarkPaidOffline:
    def test_transitions_walk_in_to_paid(self) -> None:
        order = _walk_in_order()
        admin_id = uuid.uuid4()
        receipt = _receipt()

        order.mark_paid_offline(receipt=receipt, admin_id=admin_id)

        assert order.status is OrderStatus.PAID
        assert order.payment_intent_id is None
        paid_events = [
            e for e in order.domain_events if isinstance(e, OrderPaidOfflineEvent)
        ]
        assert len(paid_events) == 1
        evt = paid_events[0]
        assert evt.order_id == order.id
        assert evt.admin_id == admin_id
        assert evt.method == OfflinePaymentMethod.CASH.value
        assert evt.reference == "POS-12345"
        assert evt.paid_amount == order.total_amount
        assert evt.currency == "RUB"

    def test_rejects_non_walk_in_order(self) -> None:
        order = Order.create(
            identity_id=uuid.uuid4(),
            cart_id=uuid.uuid4(),
            items=[_item()],
            currency="RUB",
            pickup_point=_pickup(),
            recipient_snapshot=_recipient_snapshot(),
        )
        with pytest.raises(OrderInvalidTransitionError):
            order.mark_paid_offline(receipt=_receipt(), admin_id=uuid.uuid4())

    def test_rejects_non_pending_status(self) -> None:
        order = _walk_in_order()
        order.mark_paid_offline(receipt=_receipt(), admin_id=uuid.uuid4())
        # Already PAID — second call must refuse.
        with pytest.raises(OrderInvalidTransitionError):
            order.mark_paid_offline(receipt=_receipt(), admin_id=uuid.uuid4())


# ---------------------------------------------------------------------------
# Refresh-recipient guard for walk-in
# ---------------------------------------------------------------------------


class TestWalkInRecipientRefreshGuard:
    def test_refresh_forbidden_for_walk_in(self) -> None:
        # FSM PAID → ON_HOLD is not a direct edge; we walk through
        # PROCURED first, where the DobroPost passport-invalid status
        # would normally trigger the hold in production.
        order = _walk_in_order()
        admin_id = uuid.uuid4()
        order.mark_paid_offline(receipt=_receipt(), admin_id=admin_id)
        order.procure(
            incoming_declaration=IncomingDeclaration.parse("CN-12345"),
            admin_id=admin_id,
        )
        order.hold(reason=HoldReason.PASSPORT_INVALID)

        with pytest.raises(WalkInRefreshRecipientForbiddenError):
            order.refresh_recipient_snapshot(fresh=_recipient_snapshot())
