"""ADR-010 §I3 / BE-6 — domain invariant: creation_source ⇔ is_walk_in.

Order aggregate в ``__attrs_post_init__`` валидирует, что:

* ``creation_source == WALK_IN`` ⇔ ``is_walk_in == True``
* ``creation_source ∈ {CART_CHECKOUT, BUY_NOW}`` ⇔ ``is_walk_in == False``

Нарушение → ``ValueError`` на конструкции. Ловит handler / repo
drift до того, как inconsistency дойдёт до DB (где её ещё раз
поймает CHECK constraint ``ck_orders_walk_in_source_consistent``).

Sprint 1.5 / 2026-05-19.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from src.modules.order.domain.entities import Order, OrderItem
from src.modules.order.domain.recipient_snapshot import RecipientSnapshot
from src.modules.order.domain.value_objects import (
    OrderCreationSource,
    PickupCarrier,
    PickupPointPreference,
)
from src.shared.domain.supplier_type import SupplierType

pytestmark = pytest.mark.unit

_NOW = datetime.now(UTC)


def _item() -> OrderItem:
    return OrderItem(
        id=uuid.uuid4(),
        sku_id=uuid.uuid4(),
        product_id=uuid.uuid4(),
        variant_id=uuid.uuid4(),
        product_name="x",
        variant_label=None,
        supplier_type=SupplierType.LOCAL,
        quantity=1,
        unit_price_amount=1000,
        currency="RUB",
    )


def _snapshot() -> RecipientSnapshot:
    return RecipientSnapshot(
        recipient_id=str(uuid.uuid4()),
        full_name_ru="x",
        full_name_lat="x",
        phone="+79108897762",
        email="x@example.com",
    )


def _pickup() -> PickupPointPreference:
    return PickupPointPreference(carrier=PickupCarrier.CDEK, point_id="MSK-1")


def test_create_buy_now_sets_creation_source() -> None:
    order = Order.create(
        identity_id=uuid.uuid4(),
        cart_id=uuid.uuid4(),
        items=[_item()],
        currency="RUB",
        pickup_point=_pickup(),
        recipient_snapshot=_snapshot(),
        creation_source=OrderCreationSource.BUY_NOW,
    )
    assert order.creation_source is OrderCreationSource.BUY_NOW
    assert order.is_walk_in is False


def test_create_default_cart_checkout() -> None:
    """Backward-compat: omit creation_source kwarg → CART_CHECKOUT."""
    order = Order.create(
        identity_id=uuid.uuid4(),
        cart_id=uuid.uuid4(),
        items=[_item()],
        currency="RUB",
        pickup_point=_pickup(),
        recipient_snapshot=_snapshot(),
    )
    assert order.creation_source is OrderCreationSource.CART_CHECKOUT
    assert order.is_walk_in is False


def test_create_walk_in_factory_sets_walk_in_source() -> None:
    order = Order.create_walk_in(
        identity_id=uuid.uuid4(),
        items=[_item()],
        currency="RUB",
        pickup_point=_pickup(),
        recipient_snapshot=_snapshot(),
    )
    assert order.creation_source is OrderCreationSource.WALK_IN
    assert order.is_walk_in is True


def test_invariant_rejects_walk_in_source_without_flag() -> None:
    """WALK_IN + is_walk_in=False → ValueError at construction."""
    with pytest.raises(ValueError, match="creation_source/is_walk_in mismatch"):
        Order(
            id=uuid.uuid4(),
            identity_id=uuid.uuid4(),
            cart_id=uuid.uuid4(),
            status=__import__(
                "src.modules.order.domain.value_objects", fromlist=["OrderStatus"]
            ).OrderStatus.PENDING,
            total_amount=1000,
            currency="RUB",
            cny_rate_at_checkout=None,
            pickup_point=_pickup(),
            recipient_snapshot=_snapshot(),
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
            created_at=_NOW,
            updated_at=_NOW,
            version=0,
            delivery_quote_id=None,
            delivery_amount=0,
            is_walk_in=False,  # ← inconsistent
            creation_source=OrderCreationSource.WALK_IN,
            items=[_item()],
        )


def test_invariant_rejects_cart_source_with_walk_in_flag() -> None:
    """CART_CHECKOUT + is_walk_in=True → ValueError at construction."""
    with pytest.raises(ValueError, match="creation_source/is_walk_in mismatch"):
        Order(
            id=uuid.uuid4(),
            identity_id=uuid.uuid4(),
            cart_id=uuid.uuid4(),
            status=__import__(
                "src.modules.order.domain.value_objects", fromlist=["OrderStatus"]
            ).OrderStatus.PENDING,
            total_amount=1000,
            currency="RUB",
            cny_rate_at_checkout=None,
            pickup_point=_pickup(),
            recipient_snapshot=_snapshot(),
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
            created_at=_NOW,
            updated_at=_NOW,
            version=0,
            delivery_quote_id=None,
            delivery_amount=0,
            is_walk_in=True,  # ← inconsistent with default CART_CHECKOUT
            items=[_item()],
        )
