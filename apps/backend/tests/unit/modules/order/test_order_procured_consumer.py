"""Unit tests for ``OrderProcuredConsumer`` (D1.2 / ORD-006)."""

from __future__ import annotations

import uuid
from typing import Any

import pytest

from src.modules.order.application.commands.hold_order import HoldOrderCommand
from src.modules.order.application.consumers.order_procured import (
    OrderProcuredConsumer,
)
from src.modules.order.domain.entities import Order, OrderItem
from src.modules.order.domain.recipient_snapshot import RecipientSnapshot
from src.modules.order.domain.value_objects import (
    CancellationReason,
    HoldReason,
    IncomingDeclaration,
    PickupCarrier,
    PickupPointPreference,
)
from src.shared.domain.supplier_type import SupplierType

pytestmark = pytest.mark.unit


def _recipient_snapshot() -> RecipientSnapshot:
    from datetime import date

    return RecipientSnapshot(
        recipient_id=str(uuid.uuid4()),
        full_name_ru="Иван Иванов",
        full_name_lat="Ivan Ivanov",
        phone="+79108897762",
        email="user@example.com",
        passport_serial="1234",
        passport_number="567890",
        passport_issue_date=date(2015, 5, 22),
        birth_date=date(1990, 1, 1),
        inn="500100732272",
    )


def _procured_order(*, with_attached: bool = False) -> Order:
    items = [
        OrderItem(
            id=uuid.uuid4(),
            sku_id=uuid.uuid4(),
            product_id=uuid.uuid4(),
            variant_id=uuid.uuid4(),
            product_name="Кеды",
            variant_label="42",
            supplier_type=SupplierType.CROSS_BORDER,
            quantity=1,
            unit_price_amount=12000,
            currency="RUB",
        )
    ]
    order = Order.create(
        identity_id=uuid.uuid4(),
        cart_id=uuid.uuid4(),
        items=items,
        currency="RUB",
        pickup_point=PickupPointPreference(
            carrier=PickupCarrier.CDEK, point_id="MSK-001"
        ),
        recipient_snapshot=_recipient_snapshot(),
    )
    order.mark_paid(payment_intent_id=uuid.uuid4())
    order.procure(
        incoming_declaration=IncomingDeclaration.parse("IN12345"),
        admin_id=uuid.uuid4(),
    )
    if with_attached:
        order.attach_cross_border_shipment(uuid.uuid4())
    order.clear_domain_events()
    return order


class _FakeOrderRepo:
    def __init__(self, order: Order | None = None) -> None:
        self._order = order
        self.update_calls: list[uuid.UUID] = []

    async def get(self, order_id: uuid.UUID) -> Order | None:
        return self._order if self._order and self._order.id == order_id else None

    async def get_for_update(self, order_id: uuid.UUID) -> Order | None:
        return await self.get(order_id)

    async def update(self, order: Order) -> Order:
        self.update_calls.append(order.id)
        return order


class _FakeDobroPost:
    def __init__(self, *, raise_exc: Exception | None = None) -> None:
        self._raise = raise_exc
        self.calls: list[uuid.UUID] = []

    async def book_cross_border(
        self, *, order_id, identity_id, incoming_declaration, idempotency_key
    ):
        self.calls.append(order_id)
        if self._raise is not None:
            raise self._raise
        return uuid.uuid4()

    async def cancel_cross_border(self, *, shipment_id, idempotency_key): ...
    async def update_recipient(self, *, order_id, idempotency_key): ...


class _FakeHoldHandler:
    def __init__(self) -> None:
        self.calls: list[HoldOrderCommand] = []

    async def handle(self, cmd: HoldOrderCommand) -> None:
        self.calls.append(cmd)


class _NullLogger:
    def bind(self, **_: Any) -> _NullLogger:
        return self

    def info(self, *_: Any, **__: Any) -> None: ...
    def warning(self, *_: Any, **__: Any) -> None: ...
    def error(self, *_: Any, **__: Any) -> None: ...
    def critical(self, *_: Any, **__: Any) -> None: ...
    def debug(self, *_: Any, **__: Any) -> None: ...
    def exception(self, *_: Any, **__: Any) -> None: ...


class _FakeUow:
    def __init__(self) -> None:
        self.commits = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_: Any) -> None:
        return None

    async def flush(self): ...
    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self): ...
    def register_aggregate(self, _aggregate): ...
    def enqueue_external_event(self, **_): ...


def _consumer(
    order: Order | None,
    *,
    raise_exc: Exception | None = None,
):
    repo = _FakeOrderRepo(order)
    dp = _FakeDobroPost(raise_exc=raise_exc)
    hold = _FakeHoldHandler()
    uow = _FakeUow()
    return (
        OrderProcuredConsumer(repo, dp, hold, uow, _NullLogger()),  # ty: ignore[invalid-argument-type]
        repo,
        dp,
        hold,
    )


async def test_books_dobropost_and_attaches_shipment() -> None:
    order = _procured_order()
    consumer, repo, dp, hold = _consumer(order)
    await consumer.handle({"order_id": str(order.id)})

    assert dp.calls == [order.id]
    assert hold.calls == []
    assert order.cross_border_shipment_id is not None
    assert order.id in repo.update_calls


async def test_falls_back_to_hold_on_dobropost_failure() -> None:
    order = _procured_order()
    consumer, repo, dp, hold = _consumer(order, raise_exc=RuntimeError("DobroPost 503"))
    await consumer.handle({"order_id": str(order.id)})

    assert dp.calls == [order.id]
    assert len(hold.calls) == 1
    assert hold.calls[0].reason == HoldReason.BOOKING_FAILED
    assert hold.calls[0].order_id == order.id
    # Attach NOT performed.
    assert order.cross_border_shipment_id is None
    assert repo.update_calls == []


async def test_idempotent_when_shipment_already_attached() -> None:
    order = _procured_order(with_attached=True)
    consumer, repo, dp, hold = _consumer(order)
    await consumer.handle({"order_id": str(order.id)})

    assert dp.calls == []  # no booking performed
    assert hold.calls == []
    assert repo.update_calls == []


async def test_skip_when_status_no_longer_procured() -> None:
    order = _procured_order()
    # Concurrent cancel before consumer ran.
    order.cancel(reason=CancellationReason.MERCHANT_FORCE_CANCEL)
    consumer, repo, dp, hold = _consumer(order)
    await consumer.handle({"order_id": str(order.id)})

    assert dp.calls == []
    assert hold.calls == []
    assert repo.update_calls == []


async def test_skip_on_missing_order() -> None:
    consumer, _repo, dp, hold = _consumer(None)
    await consumer.handle({"order_id": str(uuid.uuid4())})
    assert dp.calls == []
    assert hold.calls == []


async def test_skip_on_bad_payload() -> None:
    consumer, _repo, dp, hold = _consumer(None)
    await consumer.handle({"order_id": "not-a-uuid"})
    assert dp.calls == []
    assert hold.calls == []
