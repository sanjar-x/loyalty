"""Unit tests for the order-lifecycle Telegram notifier (T-2 / D3.1).

Pure logic — no DB, no aiogram. The chat lookup and notifier ports
are stubbed so we can exercise the message-formatting branches and
the early-return paths (missing order_id, order not found, customer
not Telegram-linked) without spinning up Postgres or making real
Bot API calls.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest

from src.modules.order.application.consumers.telegram_notifications import (
    TelegramOrderNotifier,
)
from src.modules.order.application.ports import (
    ITelegramChatLookup,
    ITelegramNotifier,
)
from src.modules.order.domain.entities import Order, OrderItem
from src.modules.order.domain.recipient_snapshot import RecipientSnapshot
from src.modules.order.domain.value_objects import (
    PickupCarrier,
    PickupPointPreference,
)
from src.shared.domain.supplier_type import SupplierType

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Test doubles
# ---------------------------------------------------------------------------


class _StubChatLookup(ITelegramChatLookup):
    def __init__(self, mapping: dict[uuid.UUID, int | None]) -> None:
        self._mapping = mapping
        self.calls: list[uuid.UUID] = []

    async def get_chat_id(self, identity_id: uuid.UUID) -> int | None:
        self.calls.append(identity_id)
        return self._mapping.get(identity_id)


class _StubNotifier(ITelegramNotifier):
    def __init__(self) -> None:
        self.sent: list[tuple[int, str]] = []

    async def send_html(self, *, chat_id: int, html: str) -> None:
        self.sent.append((chat_id, html))


class _StubOrderRepo:
    def __init__(self, orders: dict[uuid.UUID, Order]) -> None:
        self._orders = orders

    async def get(self, order_id: uuid.UUID) -> Order | None:
        return self._orders.get(order_id)

    async def get_for_update(self, order_id: uuid.UUID) -> Order | None:
        return self._orders.get(order_id)

    async def add(self, order: Order) -> Order:  # pragma: no cover — unused
        return order

    async def update(self, order: Order) -> Order:  # pragma: no cover — unused
        return order


class _NullLogger:
    def bind(self, **_: Any) -> _NullLogger:
        return self

    def info(self, *_: Any, **__: Any) -> None: ...
    def warning(self, *_: Any, **__: Any) -> None: ...
    def error(self, *_: Any, **__: Any) -> None: ...
    def critical(self, *_: Any, **__: Any) -> None: ...
    def debug(self, *_: Any, **__: Any) -> None: ...
    def exception(self, *_: Any, **__: Any) -> None: ...


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _build_order(
    *,
    identity_id: uuid.UUID | None = None,
    carrier: PickupCarrier = PickupCarrier.CDEK,
) -> Order:
    """Build a minimal Order aggregate suitable for notifier tests.

    Domain validation requires at least one OrderItem and a recipient
    snapshot — we synthesise both with placeholder values that pass
    the invariants.
    """
    identity_id = identity_id or uuid.uuid4()
    item = OrderItem(
        id=uuid.uuid4(),
        sku_id=uuid.uuid4(),
        product_id=uuid.uuid4(),
        variant_id=uuid.uuid4(),
        product_name="Test product",
        variant_label=None,
        supplier_type=SupplierType.CROSS_BORDER,
        quantity=1,
        unit_price_amount=10_000,
        currency="RUB",
    )
    snapshot = RecipientSnapshot(
        recipient_id=str(uuid.uuid4()),
        full_name_ru="Иванов Иван",
        full_name_lat="Ivanov Ivan",
        phone="+79001112233",
        email="ivan@example.com",
        passport_serial="1234",
        passport_number="567890",
        passport_issue_date=datetime(2010, 1, 1, tzinfo=UTC).date(),
        birth_date=datetime(1990, 1, 1, tzinfo=UTC).date(),
        inn="500100732259",
    )
    return Order.create(
        identity_id=identity_id,
        cart_id=uuid.uuid4(),
        items=[item],
        currency="RUB",
        pickup_point=PickupPointPreference(carrier=carrier, point_id="PVZ-MSK-1"),
        recipient_snapshot=snapshot,
        cny_rate_at_checkout=Decimal("12.50"),
    )


# ---------------------------------------------------------------------------
# Happy paths — one per event handler
# ---------------------------------------------------------------------------


@pytest.fixture
def chat_id() -> int:
    return 123_456_789


def _build_notifier(
    *,
    order: Order | None = None,
    chat_id: int | None = None,
) -> tuple[TelegramOrderNotifier, _StubNotifier]:
    orders: dict[uuid.UUID, Order] = {order.id: order} if order is not None else {}
    chat_mapping: dict[uuid.UUID, int | None] = {}
    if order is not None:
        chat_mapping[order.identity_id] = chat_id
    notifier_stub = _StubNotifier()
    consumer = TelegramOrderNotifier(
        order_repo=_StubOrderRepo(orders),  # ty:ignore[invalid-argument-type]
        chat_lookup=_StubChatLookup(chat_mapping),
        notifier=notifier_stub,
        logger=_NullLogger(),  # ty:ignore[invalid-argument-type]
    )
    return consumer, notifier_stub


async def test_on_order_procured_sends_message(chat_id: int) -> None:
    order = _build_order()
    consumer, notifier = _build_notifier(order=order, chat_id=chat_id)
    await consumer.on_order_procured({"order_id": str(order.id)})
    assert len(notifier.sent) == 1
    sent_chat, html = notifier.sent[0]
    assert sent_chat == chat_id
    assert order.number.value in html
    assert "выкуплен" in html


async def test_on_order_arrived_in_ru_sends_message(chat_id: int) -> None:
    order = _build_order()
    consumer, notifier = _build_notifier(order=order, chat_id=chat_id)
    await consumer.on_order_arrived_in_ru({"order_id": str(order.id)})
    assert len(notifier.sent) == 1
    assert "прибыл в Россию" in notifier.sent[0][1]


async def test_on_order_entered_last_mile_includes_carrier_label(
    chat_id: int,
) -> None:
    order = _build_order(carrier=PickupCarrier.YANDEX)
    consumer, notifier = _build_notifier(order=order, chat_id=chat_id)
    await consumer.on_order_entered_last_mile({"order_id": str(order.id)})
    assert len(notifier.sent) == 1
    assert "Яндекс Доставку" in notifier.sent[0][1]


async def test_on_order_awaiting_pickup_sends_message(chat_id: int) -> None:
    order = _build_order()
    consumer, notifier = _build_notifier(order=order, chat_id=chat_id)
    await consumer.on_order_awaiting_pickup({"order_id": str(order.id)})
    assert len(notifier.sent) == 1
    assert "пункте выдачи" in notifier.sent[0][1]


async def test_on_order_delivered_sends_message(chat_id: int) -> None:
    order = _build_order()
    consumer, notifier = _build_notifier(order=order, chat_id=chat_id)
    await consumer.on_order_delivered({"order_id": str(order.id)})
    assert len(notifier.sent) == 1
    assert "доставлен" in notifier.sent[0][1]


# ---------------------------------------------------------------------------
# Skip paths
# ---------------------------------------------------------------------------


async def test_missing_order_id_is_skipped() -> None:
    consumer, notifier = _build_notifier()
    await consumer.on_order_procured({})
    assert notifier.sent == []


async def test_bad_order_id_is_skipped() -> None:
    consumer, notifier = _build_notifier()
    await consumer.on_order_procured({"order_id": "not-a-uuid"})
    assert notifier.sent == []


async def test_order_missing_in_repo_is_skipped() -> None:
    consumer, notifier = _build_notifier()
    await consumer.on_order_procured({"order_id": str(uuid.uuid4())})
    assert notifier.sent == []


async def test_customer_without_telegram_link_is_skipped() -> None:
    """Order exists, but the customer has no Telegram-linked account."""
    order = _build_order()
    # chat_id=None means the lookup returns None for this identity.
    consumer, notifier = _build_notifier(order=order, chat_id=None)
    await consumer.on_order_procured({"order_id": str(order.id)})
    assert notifier.sent == []


async def test_unknown_carrier_falls_back_to_raw_value(chat_id: int) -> None:
    """Carrier label maps every known value — fallback prints the raw code."""
    order = _build_order(carrier=PickupCarrier.POCHTA)
    consumer, notifier = _build_notifier(order=order, chat_id=chat_id)
    await consumer.on_order_entered_last_mile({"order_id": str(order.id)})
    assert "Почту России" in notifier.sent[0][1]
