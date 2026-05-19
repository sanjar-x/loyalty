"""Unit tests for the ``record_history`` helper.

These tests use a fake ``IOrderStateHistoryWriter`` so we exercise the
mapping logic without spinning up a real session.
"""

import uuid
from datetime import datetime
from decimal import Decimal

import pytest

from src.modules.order.application._history import record_history
from src.modules.order.domain.entities import Order, OrderItem
from src.modules.order.domain.events import (
    OrderArrivedInRuEvent,
    OrderEnteredHoldEvent,
    OrderResumedFromHoldEvent,
)
from src.modules.order.domain.interfaces import (
    HistoryActor,
    IOrderStateHistoryWriter,
)
from src.modules.order.domain.recipient_snapshot import RecipientSnapshot
from src.modules.order.domain.value_objects import (
    HoldReason,
    IncomingDeclaration,
    OrderStatus,
    PickupCarrier,
    PickupPointPreference,
)
from src.shared.domain.supplier_type import SupplierType

pytestmark = pytest.mark.unit


class _FakeHistoryWriter(IOrderStateHistoryWriter):
    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def append(
        self,
        *,
        order_id,
        from_status,
        to_status,
        event_type,
        event_id,
        actor: HistoryActor,
        metadata,
        occurred_at: datetime,
    ) -> None:
        self.calls.append(
            {
                "order_id": order_id,
                "from_status": from_status,
                "to_status": to_status,
                "event_type": event_type,
                "event_id": event_id,
                "actor_type": actor.actor_type,
                "actor_id": actor.actor_id,
                "metadata": metadata,
                "occurred_at": occurred_at,
            }
        )


def _recipient_snapshot() -> RecipientSnapshot:
    return RecipientSnapshot(
        recipient_id=str(uuid.uuid4()),
        full_name_ru="Иван Иванов",
        full_name_lat="Ivan Ivanov",
        phone="+79108897762",
        email="ivan@example.com",
    )


def _order() -> Order:
    from tests.factories.passport_factories import make_passport_snapshot

    snap = make_passport_snapshot()
    return Order.create(
        identity_id=uuid.uuid4(),
        cart_id=uuid.uuid4(),
        items=[
            OrderItem(
                id=uuid.uuid4(),
                sku_id=uuid.uuid4(),
                product_id=uuid.uuid4(),
                variant_id=uuid.uuid4(),
                product_name="Item",
                variant_label=None,
                supplier_type=SupplierType.CROSS_BORDER,
                quantity=1,
                unit_price_amount=10_000,
                currency="RUB",
            )
        ],
        currency="RUB",
        pickup_point=PickupPointPreference(
            carrier=PickupCarrier.CDEK, point_id="MSK-1"
        ),
        recipient_snapshot=_recipient_snapshot(),
        cny_rate_at_checkout=Decimal("13.5"),
        passport_id=uuid.UUID(snap.passport_id),
        passport_snapshot=snap,
    )


@pytest.mark.asyncio
class TestRecordHistory:
    async def test_create_event_yields_pending_with_null_from(self) -> None:
        order = _order()
        writer = _FakeHistoryWriter()
        await record_history(
            order=order,
            history_writer=writer,
            actor=HistoryActor(actor_type="customer", actor_id="u-1"),
            pre_commit_status=None,
        )
        assert len(writer.calls) == 1
        call = writer.calls[0]
        assert call["from_status"] is None
        assert call["to_status"] == OrderStatus.PENDING
        assert call["event_type"] == "OrderCreatedEvent"

    async def test_paid_transition(self) -> None:
        order = _order()
        intent_id = uuid.uuid4()
        order.attach_payment_intent(intent_id)
        order.clear_domain_events()
        order.mark_paid(payment_intent_id=intent_id)

        writer = _FakeHistoryWriter()
        await record_history(
            order=order,
            history_writer=writer,
            actor=HistoryActor(actor_type="system", actor_id="payment"),
            pre_commit_status=OrderStatus.PENDING,
        )
        assert len(writer.calls) == 1
        assert writer.calls[0]["from_status"] == OrderStatus.PENDING
        assert writer.calls[0]["to_status"] == OrderStatus.PAID
        assert writer.calls[0]["event_type"] == "OrderPaidEvent"

    async def test_hold_then_resume_chain(self) -> None:
        order = _order()
        intent_id = uuid.uuid4()
        order.attach_payment_intent(intent_id)
        order.mark_paid(payment_intent_id=intent_id)
        order.procure(
            incoming_declaration=IncomingDeclaration.parse("CN-1"),
            admin_id=uuid.uuid4(),
        )
        order.clear_domain_events()

        order.hold(reason=HoldReason.PASSPORT_INVALID)
        # hold sets pre_hold_status to PROCURED, then resume goes back.
        order.resume_from_hold()

        writer = _FakeHistoryWriter()
        await record_history(
            order=order,
            history_writer=writer,
            actor=HistoryActor(actor_type="manager", actor_id="resume"),
            pre_commit_status=OrderStatus.PROCURED,
        )
        statuses = [(c["from_status"], c["to_status"]) for c in writer.calls]
        assert statuses == [
            (OrderStatus.PROCURED, OrderStatus.ON_HOLD),
            (OrderStatus.ON_HOLD, OrderStatus.PROCURED),
        ]

    async def test_informational_event_skipped(self) -> None:
        order = _order()
        order.clear_domain_events()
        # Manually push a ``OrderPickupPointChangedEvent`` (informational).
        from src.modules.order.domain.events import OrderPickupPointChangedEvent

        order.add_domain_event(
            OrderPickupPointChangedEvent(
                order_id=order.id,
                new_carrier="yandex",
                new_point_id="YDX-1",
            )
        )
        writer = _FakeHistoryWriter()
        await record_history(
            order=order,
            history_writer=writer,
            actor=HistoryActor(actor_type="customer", actor_id="u-1"),
            pre_commit_status=OrderStatus.PENDING,
        )
        assert writer.calls == []

    async def test_metadata_is_jsonable(self) -> None:
        order = _order()
        order.clear_domain_events()
        order.add_domain_event(
            OrderArrivedInRuEvent(
                order_id=order.id,
                cross_border_shipment_id=uuid.uuid4(),
            )
        )
        writer = _FakeHistoryWriter()
        await record_history(
            order=order,
            history_writer=writer,
            actor=HistoryActor(actor_type="webhook", actor_id="dobropost"),
            pre_commit_status=OrderStatus.PROCURED,
        )
        meta = writer.calls[0]["metadata"]
        assert meta is not None
        # cross_border_shipment_id must be normalised to a string
        assert isinstance(meta["cross_border_shipment_id"], str)
        # the helper drops the bookkeeping fields
        assert "event_id" not in meta
        assert "occurred_at" not in meta

    async def test_resume_event_uses_payload_status(self) -> None:
        order = _order()
        order.clear_domain_events()
        order.add_domain_event(
            OrderResumedFromHoldEvent(
                order_id=order.id,
                resumed_to_status=OrderStatus.ARRIVED_IN_RU.value,
            )
        )
        writer = _FakeHistoryWriter()
        await record_history(
            order=order,
            history_writer=writer,
            actor=HistoryActor(actor_type="manager", actor_id="resume"),
            pre_commit_status=OrderStatus.ON_HOLD,
        )
        assert len(writer.calls) == 1
        assert writer.calls[0]["from_status"] == OrderStatus.ON_HOLD
        assert writer.calls[0]["to_status"] == OrderStatus.ARRIVED_IN_RU

    async def test_no_events_no_calls(self) -> None:
        order = _order()
        order.clear_domain_events()
        writer = _FakeHistoryWriter()
        await record_history(
            order=order,
            history_writer=writer,
            actor=HistoryActor(actor_type="customer", actor_id="u-1"),
            pre_commit_status=OrderStatus.PENDING,
        )
        assert writer.calls == []


# Ensure unused import is referenced (it is — for resume payload shape).
assert OrderEnteredHoldEvent is not None
