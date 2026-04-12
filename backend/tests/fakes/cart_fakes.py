"""Fake implementations for cart domain tests."""

from __future__ import annotations

import uuid
from datetime import datetime

from src.modules.cart.domain.entities import Cart
from src.modules.cart.domain.interfaces import (
    ICartRepository,
    IOrderCreationService,
    IPickupPointReadService,
    ISkuReadService,
)
from src.modules.cart.domain.value_objects import CheckoutSnapshot, SkuSnapshot


class FakeCartRepository(ICartRepository):
    """In-memory cart repository for unit tests."""

    def __init__(self) -> None:
        self._store: dict[uuid.UUID, Cart] = {}
        self._snapshots: dict[uuid.UUID, CheckoutSnapshot] = {}
        self._attempts: dict[uuid.UUID, dict] = {}

    async def add(self, cart: Cart) -> Cart:
        self._store[cart.id] = cart
        return cart

    async def get(self, cart_id: uuid.UUID) -> Cart | None:
        return self._store.get(cart_id)

    async def get_for_update(self, cart_id: uuid.UUID) -> Cart | None:
        return self._store.get(cart_id)

    async def get_active_by_identity(self, identity_id: uuid.UUID) -> Cart | None:
        for cart in self._store.values():
            if cart.identity_id == identity_id and cart.status.value == "active":
                return cart
        return None

    async def get_active_by_identity_for_update(self, identity_id: uuid.UUID) -> Cart | None:
        return await self.get_active_by_identity(identity_id)

    async def get_active_or_frozen_by_identity(self, identity_id: uuid.UUID) -> Cart | None:
        for cart in self._store.values():
            if cart.identity_id == identity_id and cart.status.value in ("active", "frozen"):
                return cart
        return None

    async def get_active_by_anonymous(self, anonymous_token: str) -> Cart | None:
        for cart in self._store.values():
            if cart.anonymous_token == anonymous_token and cart.status.value == "active":
                return cart
        return None

    async def update(self, cart: Cart) -> Cart:
        self._store[cart.id] = cart
        return cart

    async def save_checkout_snapshot(self, snapshot: CheckoutSnapshot) -> None:
        self._snapshots[snapshot.id] = snapshot

    async def update_checkout_snapshot(self, snapshot: CheckoutSnapshot) -> None:
        self._snapshots[snapshot.id] = snapshot

    async def get_checkout_snapshot(
        self, snapshot_id: uuid.UUID
    ) -> CheckoutSnapshot | None:
        return self._snapshots.get(snapshot_id)

    async def create_checkout_attempt(
        self,
        *,
        attempt_id: uuid.UUID,
        cart_id: uuid.UUID,
        snapshot_id: uuid.UUID,
    ) -> None:
        self._attempts[attempt_id] = {
            "id": attempt_id,
            "cart_id": cart_id,
            "snapshot_id": snapshot_id,
            "status": "pending",
            "created_at": datetime.now(),
        }

    async def get_pending_checkout_attempt(self, cart_id: uuid.UUID) -> dict | None:
        for attempt in self._attempts.values():
            if attempt["cart_id"] == cart_id and attempt["status"] == "pending":
                return attempt
        return None

    async def resolve_checkout_attempt(
        self,
        attempt_id: uuid.UUID,
        *,
        status: str,
        resolved_at: datetime,
    ) -> None:
        if attempt_id in self._attempts:
            self._attempts[attempt_id]["status"] = status
            self._attempts[attempt_id]["resolved_at"] = resolved_at


class FakeSkuReadService(ISkuReadService):
    """In-memory SKU read service for unit tests."""

    def __init__(self) -> None:
        self._store: dict[uuid.UUID, SkuSnapshot] = {}

    def seed(self, *snapshots: SkuSnapshot) -> None:
        for s in snapshots:
            self._store[s.sku_id] = s

    async def get_sku_snapshot(self, sku_id: uuid.UUID) -> SkuSnapshot | None:
        return self._store.get(sku_id)

    async def get_sku_snapshots_batch(
        self, sku_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, SkuSnapshot]:
        return {sid: self._store[sid] for sid in sku_ids if sid in self._store}

    async def check_skus_active(
        self, sku_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, bool]:
        return {
            sid: self._store[sid].is_active
            for sid in sku_ids
            if sid in self._store
        }


class FakePickupPointReadService(IPickupPointReadService):
    """Stub pickup point service — always returns True by default."""

    def __init__(self, *, exists_result: bool = True) -> None:
        self._exists_result = exists_result

    async def exists(self, pickup_point_id: uuid.UUID) -> bool:
        return self._exists_result


class FakeOrderCreationService(IOrderCreationService):
    """Stub order creation service — returns a fixed UUID."""

    def __init__(self) -> None:
        self.created_orders: list[dict] = []

    async def create_order_from_cart(
        self,
        cart_id: uuid.UUID,
        checkout_id: uuid.UUID,
        snapshot: CheckoutSnapshot,
    ) -> uuid.UUID:
        order_id = uuid.uuid4()
        self.created_orders.append(
            {"order_id": order_id, "cart_id": cart_id, "checkout_id": checkout_id}
        )
        return order_id
