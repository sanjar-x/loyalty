"""Unit tests for Cart value objects."""

import uuid

import pytest

from src.modules.cart.domain.value_objects import (
    CartStatus,
    CheckoutItemSnapshot,
    CheckoutSnapshot,
    SkuSnapshot,
)


@pytest.mark.unit
class TestCartStatus:
    def test_status_values(self) -> None:
        assert CartStatus.ACTIVE == "active"
        assert CartStatus.FROZEN == "frozen"
        assert CartStatus.MERGED == "merged"
        assert CartStatus.ORDERED == "ordered"

    def test_status_is_str_enum(self) -> None:
        assert isinstance(CartStatus.ACTIVE, str)


@pytest.mark.unit
class TestSkuSnapshot:
    def test_construction(self) -> None:
        snap = SkuSnapshot(
            sku_id=uuid.uuid4(),
            product_id=uuid.uuid4(),
            variant_id=uuid.uuid4(),
            product_name="Test",
            variant_label="XL",
            image_url=None,
            price_amount=10000,
            currency="RUB",
            supplier_type="local",
            is_active=True,
        )
        assert snap.price_amount == 10000
        assert snap.is_active is True

    def test_immutability(self) -> None:
        snap = SkuSnapshot(
            sku_id=uuid.uuid4(),
            product_id=uuid.uuid4(),
            variant_id=uuid.uuid4(),
            product_name="Test",
            variant_label=None,
            image_url=None,
            price_amount=5000,
            currency="RUB",
            supplier_type="cross_border",
            is_active=True,
        )
        with pytest.raises(AttributeError):
            snap.price_amount = 9999  # ty:ignore[invalid-assignment]


@pytest.mark.unit
class TestCheckoutSnapshot:
    def test_construction_with_items(self) -> None:
        items = (
            CheckoutItemSnapshot(
                sku_id=uuid.uuid4(),
                quantity=2,
                unit_price_amount=5000,
                currency="RUB",
            ),
            CheckoutItemSnapshot(
                sku_id=uuid.uuid4(),
                quantity=1,
                unit_price_amount=3000,
                currency="RUB",
            ),
        )
        snap = CheckoutSnapshot(
            id=uuid.uuid4(),
            cart_id=uuid.uuid4(),
            items=items,
            pickup_point_id=uuid.uuid4(),
            total_amount=13000,
            currency="RUB",
            created_at=None,  # ty:ignore[invalid-argument-type]
            expires_at=None,  # ty:ignore[invalid-argument-type]
        )
        assert len(snap.items) == 2
        assert snap.total_amount == 13000

    def test_items_tuple_immutable(self) -> None:
        snap = CheckoutSnapshot(
            id=uuid.uuid4(),
            cart_id=uuid.uuid4(),
            items=(),
            pickup_point_id=uuid.uuid4(),
            total_amount=0,
            currency="RUB",
            created_at=None,  # ty:ignore[invalid-argument-type]
            expires_at=None,  # ty:ignore[invalid-argument-type]
        )
        with pytest.raises(AttributeError):
            snap.items = ()  # ty:ignore[invalid-assignment]
