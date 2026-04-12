"""Unit tests for Cart domain event emission."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from src.modules.cart.domain.entities import Cart
from src.modules.cart.domain.events import (
    CartClearedEvent,
    CartCreatedEvent,
    CartFrozenEvent,
    CartItemAddedEvent,
    CartItemQuantityUpdatedEvent,
    CartItemRemovedEvent,
    CartMergedEvent,
    CartOrderedEvent,
    CartUnfrozenEvent,
)
from src.modules.cart.domain.value_objects import (
    CartStatus,
    CheckoutItemSnapshot,
    CheckoutSnapshot,
)
from tests.factories.cart_builder import CartBuilder, CartItemBuilder
from tests.factories.sku_mothers import SkuSnapshotMother


@pytest.mark.unit
class TestCartCreatedEvent:
    def test_create_emits_cart_created(self) -> None:
        cart = Cart.create(identity_id=uuid.uuid4())
        assert len(cart.domain_events) == 1
        event = cart.domain_events[0]
        assert isinstance(event, CartCreatedEvent)
        assert event.cart_id == cart.id
        assert event.aggregate_id == str(cart.id)
        assert event.aggregate_type == "cart"
        assert event.event_type == "CartCreatedEvent"

    def test_guest_cart_created_has_token(self) -> None:
        cart = Cart.create(anonymous_token="tok123")
        event = cart.domain_events[0]
        assert isinstance(event, CartCreatedEvent)
        assert event.anonymous_token == "tok123"
        assert event.identity_id is None


@pytest.mark.unit
class TestItemEvents:
    def test_add_item_emits_item_added(self) -> None:
        cart = CartBuilder().build()
        snap = SkuSnapshotMother.active()
        cart.add_item(snap, quantity=3)
        events = cart.domain_events
        assert len(events) == 1
        assert isinstance(events[0], CartItemAddedEvent)
        assert events[0].sku_id == snap.sku_id
        assert events[0].quantity == 3
        assert events[0].aggregate_id == str(cart.id)

    def test_add_duplicate_sku_emits_quantity_updated(self) -> None:
        snap = SkuSnapshotMother.active()
        cart = CartBuilder().build()
        cart.add_item(snap, 1)
        cart.clear_domain_events()
        cart.add_item(snap, 2)
        events = cart.domain_events
        assert len(events) == 1
        assert isinstance(events[0], CartItemQuantityUpdatedEvent)
        assert events[0].old_quantity == 1
        assert events[0].new_quantity == 3

    def test_remove_item_emits_item_removed(self) -> None:
        item = CartItemBuilder().build()
        cart = CartBuilder().with_items(item).build()
        cart.remove_item(item.id)
        events = cart.domain_events
        assert len(events) == 1
        assert isinstance(events[0], CartItemRemovedEvent)
        assert events[0].item_id == item.id

    def test_update_quantity_emits_event(self) -> None:
        item = CartItemBuilder().with_quantity(2).build()
        cart = CartBuilder().with_items(item).build()
        cart.update_quantity(item.id, 5)
        events = cart.domain_events
        assert len(events) == 1
        assert isinstance(events[0], CartItemQuantityUpdatedEvent)
        assert events[0].old_quantity == 2
        assert events[0].new_quantity == 5

    def test_update_quantity_to_zero_emits_removed(self) -> None:
        item = CartItemBuilder().build()
        cart = CartBuilder().with_items(item).build()
        cart.update_quantity(item.id, 0)
        events = cart.domain_events
        assert len(events) == 1
        assert isinstance(events[0], CartItemRemovedEvent)

    def test_clear_emits_cleared(self) -> None:
        items = [CartItemBuilder().build() for _ in range(3)]
        cart = CartBuilder().with_items(*items).build()
        cart.clear()
        events = cart.domain_events
        assert len(events) == 1
        assert isinstance(events[0], CartClearedEvent)
        assert events[0].cart_id == cart.id


def _make_snapshot(cart_id: uuid.UUID) -> CheckoutSnapshot:
    return CheckoutSnapshot(
        id=uuid.uuid4(),
        cart_id=cart_id,
        items=(
            CheckoutItemSnapshot(
                sku_id=uuid.uuid4(),
                quantity=1,
                unit_price_amount=10000,
                currency="RUB",
            ),
        ),
        pickup_point_id=uuid.uuid4(),
        total_amount=10000,
        currency="RUB",
        created_at=datetime.now(UTC),
        expires_at=datetime.now(UTC) + timedelta(minutes=15),
    )


@pytest.mark.unit
class TestCheckoutEvents:
    def test_freeze_emits_frozen(self) -> None:
        item = CartItemBuilder().build()
        cart = CartBuilder().with_items(item).build()
        snap = _make_snapshot(cart.id)
        cart.freeze_for_checkout(snap, snap.expires_at)
        events = cart.domain_events
        assert len(events) == 1
        assert isinstance(events[0], CartFrozenEvent)
        assert events[0].snapshot_id == snap.id

    def test_unfreeze_emits_unfrozen(self) -> None:
        cart = CartBuilder().with_status(CartStatus.FROZEN).build()
        cart.unfreeze("expired")
        events = cart.domain_events
        assert len(events) == 1
        assert isinstance(events[0], CartUnfrozenEvent)
        assert events[0].reason == "expired"

    def test_mark_ordered_emits_ordered(self) -> None:
        item = CartItemBuilder().build()
        cart = CartBuilder().with_items(item).with_status(CartStatus.FROZEN).build()
        cart.mark_ordered()
        events = cart.domain_events
        assert len(events) == 1
        assert isinstance(events[0], CartOrderedEvent)
        assert events[0].item_count == 1


@pytest.mark.unit
class TestMergeEvents:
    def test_merge_emits_merged_on_target(self) -> None:
        target = CartBuilder().build()
        source_item = CartItemBuilder().build()
        source = CartBuilder().as_guest("g").with_items(source_item).build()
        target.merge_from(source)
        target_events = target.domain_events
        assert len(target_events) == 1
        assert isinstance(target_events[0], CartMergedEvent)
        assert target_events[0].target_cart_id == target.id
        assert target_events[0].source_cart_id == source.id
        assert target_events[0].items_transferred == 1
