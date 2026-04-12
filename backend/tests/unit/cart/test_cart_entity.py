"""Unit tests for Cart aggregate root — invariants and domain methods."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from src.modules.cart.domain.entities import (
    MAX_CART_ITEMS,
    MAX_QTY_PER_ITEM,
    Cart,
)
from src.modules.cart.domain.exceptions import (
    CartEmptyError,
    CartFrozenForCheckoutError,
    CartItemLimitExceededError,
    CartItemNotFoundError,
    CartItemQuantityError,
    CartNotActiveError,
    SkuNotAvailableError,
)
from src.modules.cart.domain.value_objects import CartStatus
from tests.factories.cart_builder import CartBuilder, CartItemBuilder
from tests.factories.sku_mothers import SkuSnapshotMother
from tests.unit.cart.helpers import make_checkout_snapshot

# ---------------------------------------------------------------------------
# Factory method Cart.create()
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCartCreate:
    def test_create_with_identity(self) -> None:
        uid = uuid.uuid4()
        cart = Cart.create(identity_id=uid)
        assert cart.identity_id == uid
        assert cart.anonymous_token is None
        assert cart.status == CartStatus.ACTIVE
        assert cart.version == 0
        assert len(cart.items) == 0

    def test_create_with_anonymous_token(self) -> None:
        cart = Cart.create(anonymous_token="guest-abc")
        assert cart.identity_id is None
        assert cart.anonymous_token == "guest-abc"
        assert cart.status == CartStatus.ACTIVE

    def test_create_requires_either_identity_or_token(self) -> None:
        with pytest.raises(ValueError, match="either"):
            Cart.create()

    def test_create_rejects_both_identity_and_token(self) -> None:
        with pytest.raises(ValueError, match="cannot have both"):
            Cart.create(identity_id=uuid.uuid4(), anonymous_token="tok")


# ---------------------------------------------------------------------------
# add_item
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestAddItem:
    def test_add_new_item(self) -> None:
        cart = CartBuilder().build()
        snap = SkuSnapshotMother.active()
        item = cart.add_item(snap, quantity=2)
        assert item.sku_id == snap.sku_id
        assert item.quantity == 2
        assert len(cart.items) == 1

    def test_add_same_sku_merges_quantity(self) -> None:
        snap = SkuSnapshotMother.active()
        cart = CartBuilder().build()
        cart.add_item(snap, quantity=2)
        cart.add_item(snap, quantity=3)
        assert len(cart.items) == 1
        assert cart.items[0].quantity == 5

    def test_add_same_sku_caps_at_max(self) -> None:
        snap = SkuSnapshotMother.active()
        cart = CartBuilder().build()
        cart.add_item(snap, quantity=MAX_QTY_PER_ITEM)
        cart.add_item(snap, quantity=10)
        assert cart.items[0].quantity == MAX_QTY_PER_ITEM

    def test_add_inactive_sku_rejected(self) -> None:
        cart = CartBuilder().build()
        snap = SkuSnapshotMother.inactive()
        with pytest.raises(SkuNotAvailableError):
            cart.add_item(snap, quantity=1)

    def test_add_item_zero_quantity_rejected(self) -> None:
        cart = CartBuilder().build()
        snap = SkuSnapshotMother.active()
        with pytest.raises(CartItemQuantityError):
            cart.add_item(snap, quantity=0)

    def test_add_item_negative_quantity_rejected(self) -> None:
        cart = CartBuilder().build()
        snap = SkuSnapshotMother.active()
        with pytest.raises(CartItemQuantityError):
            cart.add_item(snap, quantity=-1)

    def test_add_item_exceeds_limit(self) -> None:
        items = [CartItemBuilder().build() for _ in range(MAX_CART_ITEMS)]
        cart = CartBuilder().with_items(*items).build()
        snap = SkuSnapshotMother.active()
        with pytest.raises(CartItemLimitExceededError):
            cart.add_item(snap, quantity=1)

    def test_add_item_on_frozen_cart_rejected(self) -> None:
        cart = CartBuilder().with_status(CartStatus.FROZEN).build()
        snap = SkuSnapshotMother.active()
        with pytest.raises(CartNotActiveError):
            cart.add_item(snap, quantity=1)


# ---------------------------------------------------------------------------
# remove_item
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRemoveItem:
    def test_remove_existing_item(self) -> None:
        item = CartItemBuilder().build()
        cart = CartBuilder().with_items(item).build()
        cart.remove_item(item.id)
        assert len(cart.items) == 0

    def test_remove_nonexistent_item_raises(self) -> None:
        cart = CartBuilder().build()
        with pytest.raises(CartItemNotFoundError):
            cart.remove_item(uuid.uuid4())


# ---------------------------------------------------------------------------
# update_quantity
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestUpdateQuantity:
    def test_update_quantity(self) -> None:
        item = CartItemBuilder().with_quantity(2).build()
        cart = CartBuilder().with_items(item).build()
        cart.update_quantity(item.id, 5)
        assert item.quantity == 5

    def test_update_quantity_to_zero_removes(self) -> None:
        item = CartItemBuilder().build()
        cart = CartBuilder().with_items(item).build()
        cart.update_quantity(item.id, 0)
        assert len(cart.items) == 0

    def test_update_quantity_negative_rejected(self) -> None:
        item = CartItemBuilder().build()
        cart = CartBuilder().with_items(item).build()
        with pytest.raises(CartItemQuantityError):
            cart.update_quantity(item.id, -1)

    def test_update_quantity_exceeds_max(self) -> None:
        item = CartItemBuilder().build()
        cart = CartBuilder().with_items(item).build()
        with pytest.raises(CartItemQuantityError):
            cart.update_quantity(item.id, MAX_QTY_PER_ITEM + 1)


# ---------------------------------------------------------------------------
# clear
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestClear:
    def test_clear_removes_all_items(self) -> None:
        items = [CartItemBuilder().build() for _ in range(3)]
        cart = CartBuilder().with_items(*items).build()
        cart.clear()
        assert len(cart.items) == 0

    def test_clear_empty_cart_ok(self) -> None:
        cart = CartBuilder().build()
        cart.clear()
        assert len(cart.items) == 0


# ---------------------------------------------------------------------------
# freeze_for_checkout / unfreeze
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFreezeUnfreeze:
    def test_freeze_active_cart_with_items(self) -> None:
        item = CartItemBuilder().build()
        cart = CartBuilder().with_items(item).build()
        snap = make_checkout_snapshot(cart.id)
        cart.freeze_for_checkout(snap, snap.expires_at)
        assert cart.status == CartStatus.FROZEN
        assert cart.frozen_until == snap.expires_at

    def test_freeze_empty_cart_raises(self) -> None:
        cart = CartBuilder().build()
        snap = make_checkout_snapshot(cart.id)
        with pytest.raises(CartEmptyError):
            cart.freeze_for_checkout(snap, snap.expires_at)

    def test_freeze_non_active_cart_raises(self) -> None:
        item = CartItemBuilder().build()
        cart = CartBuilder().with_items(item).with_status(CartStatus.ORDERED).build()
        snap = make_checkout_snapshot(cart.id)
        with pytest.raises(CartNotActiveError):
            cart.freeze_for_checkout(snap, snap.expires_at)

    def test_unfreeze_frozen_cart(self) -> None:
        item = CartItemBuilder().build()
        cart = CartBuilder().with_items(item).with_status(CartStatus.FROZEN).build()
        cart.unfreeze("cancelled")
        assert cart.status == CartStatus.ACTIVE
        assert cart.frozen_until is None

    def test_unfreeze_non_frozen_raises(self) -> None:
        cart = CartBuilder().build()
        with pytest.raises(CartNotActiveError):
            cart.unfreeze()


# ---------------------------------------------------------------------------
# mark_ordered
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestMarkOrdered:
    def test_mark_ordered_from_frozen(self) -> None:
        item = CartItemBuilder().build()
        cart = CartBuilder().with_items(item).with_status(CartStatus.FROZEN).build()
        cart.mark_ordered()
        assert cart.status == CartStatus.ORDERED

    def test_mark_ordered_from_active_raises(self) -> None:
        cart = CartBuilder().build()
        with pytest.raises(CartNotActiveError):
            cart.mark_ordered()


# ---------------------------------------------------------------------------
# merge_from
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestMerge:
    def test_merge_transfers_items(self) -> None:
        target = CartBuilder().build()
        source_item = CartItemBuilder().build()
        source = CartBuilder().as_guest("g").with_items(source_item).build()
        transferred, skipped = target.merge_from(source)
        assert transferred == 1
        assert len(skipped) == 0
        assert len(target.items) == 1
        assert source.status == CartStatus.MERGED

    def test_merge_sums_quantity_for_same_sku(self) -> None:
        sku_id = uuid.uuid4()
        target_item = CartItemBuilder().with_sku_id(sku_id).with_quantity(2).build()
        source_item = CartItemBuilder().with_sku_id(sku_id).with_quantity(3).build()
        target = CartBuilder().with_items(target_item).build()
        source = CartBuilder().as_guest("g").with_items(source_item).build()
        transferred, _skipped = target.merge_from(source)
        assert transferred == 1
        assert target_item.quantity == 5

    def test_merge_skips_items_over_limit(self) -> None:
        existing = [CartItemBuilder().build() for _ in range(MAX_CART_ITEMS)]
        target = CartBuilder().with_items(*existing).build()
        source_item = CartItemBuilder().build()
        source = CartBuilder().as_guest("g").with_items(source_item).build()
        transferred, skipped = target.merge_from(source)
        assert transferred == 0
        assert len(skipped) == 1

    def test_merge_from_frozen_source_rejected(self) -> None:
        target = CartBuilder().build()
        source = CartBuilder().as_guest("g").with_status(CartStatus.FROZEN).build()
        with pytest.raises(CartFrozenForCheckoutError):
            target.merge_from(source)


# ---------------------------------------------------------------------------
# assign_owner
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestAssignOwner:
    def test_assign_owner_to_guest_cart(self) -> None:
        cart = CartBuilder().as_guest("tok").build()
        uid = uuid.uuid4()
        cart.assign_owner(uid)
        assert cart.identity_id == uid
        assert cart.anonymous_token is None


# ---------------------------------------------------------------------------
# Utility methods
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestUtilityMethods:
    def test_is_freeze_expired_true(self) -> None:
        cart = (
            CartBuilder()
            .with_status(CartStatus.FROZEN)
            .with_frozen_until(datetime.now(UTC) - timedelta(minutes=1))
            .build()
        )
        assert cart.is_freeze_expired()

    def test_is_freeze_expired_false(self) -> None:
        cart = (
            CartBuilder()
            .with_status(CartStatus.FROZEN)
            .with_frozen_until(datetime.now(UTC) + timedelta(minutes=10))
            .build()
        )
        assert not cart.is_freeze_expired()

    def test_is_freeze_expired_not_frozen(self) -> None:
        cart = CartBuilder().build()
        assert not cart.is_freeze_expired()
