"""Unit tests for ADR-011 cross-border passport invariant on Order.create.

Verifies:

* LOCAL-only Order.create without a passport → OK.
* CROSS_BORDER Order.create without a passport → 422
  ``PASSPORT_REQUIRED_FOR_CROSS_BORDER``.
* CROSS_BORDER Order.create with a valid passport snapshot → OK.
* Pair-consistency invariant (passport_id ⇔ passport_snapshot) is
  enforced inside ``__attrs_post_init__``.
"""

import uuid
from datetime import date

import pytest

from src.modules.order.domain.entities import Order, OrderItem
from src.modules.order.domain.exceptions import (
    PassportRequiredForCrossBorderError,
)
from src.modules.order.domain.recipient_snapshot import (
    PassportSnapshot,
    RecipientSnapshot,
)
from src.modules.order.domain.value_objects import (
    PickupCarrier,
    PickupPointPreference,
)
from src.shared.domain.supplier_type import SupplierType

pytestmark = pytest.mark.unit


def _recipient_snapshot() -> RecipientSnapshot:
    return RecipientSnapshot(
        recipient_id=str(uuid.uuid4()),
        full_name_ru="Иван Иванов",
        full_name_lat="Ivan Ivanov",
        phone="+79108897762",
        email="user@example.com",
    )


def _passport_snapshot() -> PassportSnapshot:
    return PassportSnapshot(
        passport_id=str(uuid.uuid4()),
        full_name_ru="Иван Иванов",
        full_name_lat="Ivan Ivanov",
        passport_serial="1234",
        passport_number="567890",
        passport_issue_date=date(2015, 5, 22),
        birth_date=date(1990, 1, 1),
        inn="500100732272",
        validation_status="pending",
    )


def _item(supplier_type: SupplierType) -> OrderItem:
    return OrderItem(
        id=uuid.uuid4(),
        sku_id=uuid.uuid4(),
        product_id=uuid.uuid4(),
        variant_id=uuid.uuid4(),
        product_name="Test SKU",
        variant_label=None,
        supplier_type=supplier_type,
        quantity=1,
        unit_price_amount=10_000,
        currency="RUB",
    )


def _pickup() -> PickupPointPreference:
    return PickupPointPreference(carrier=PickupCarrier.CDEK, point_id="pp-1")


class TestCrossBorderInvariant:
    def test_local_order_without_passport_ok(self) -> None:
        order = Order.create(
            identity_id=uuid.uuid4(),
            cart_id=uuid.uuid4(),
            items=[_item(SupplierType.LOCAL)],
            currency="RUB",
            pickup_point=_pickup(),
            recipient_snapshot=_recipient_snapshot(),
        )
        assert order.passport_id is None
        assert order.passport_snapshot is None

    def test_cross_border_order_without_passport_rejected(self) -> None:
        with pytest.raises(PassportRequiredForCrossBorderError):
            Order.create(
                identity_id=uuid.uuid4(),
                cart_id=uuid.uuid4(),
                items=[_item(SupplierType.CROSS_BORDER)],
                currency="RUB",
                pickup_point=_pickup(),
                recipient_snapshot=_recipient_snapshot(),
            )

    def test_cross_border_order_with_passport_ok(self) -> None:
        snap = _passport_snapshot()
        order = Order.create(
            identity_id=uuid.uuid4(),
            cart_id=uuid.uuid4(),
            items=[_item(SupplierType.CROSS_BORDER)],
            currency="RUB",
            pickup_point=_pickup(),
            recipient_snapshot=_recipient_snapshot(),
            passport_id=uuid.UUID(snap.passport_id),
            passport_snapshot=snap,
        )
        assert order.passport_id is not None
        assert order.passport_snapshot is snap

    def test_passport_id_without_snapshot_rejected(self) -> None:
        with pytest.raises(ValueError):
            Order.create(
                identity_id=uuid.uuid4(),
                cart_id=uuid.uuid4(),
                items=[_item(SupplierType.LOCAL)],
                currency="RUB",
                pickup_point=_pickup(),
                recipient_snapshot=_recipient_snapshot(),
                passport_id=uuid.uuid4(),
                passport_snapshot=None,
            )

    def test_passport_snapshot_without_id_rejected(self) -> None:
        with pytest.raises(ValueError):
            Order.create(
                identity_id=uuid.uuid4(),
                cart_id=uuid.uuid4(),
                items=[_item(SupplierType.LOCAL)],
                currency="RUB",
                pickup_point=_pickup(),
                recipient_snapshot=_recipient_snapshot(),
                passport_id=None,
                passport_snapshot=_passport_snapshot(),
            )
