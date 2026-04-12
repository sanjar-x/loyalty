"""Fluent builders for Cart domain entities."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from src.modules.cart.domain.entities import Cart, CartItem
from src.modules.cart.domain.value_objects import CartStatus


class CartItemBuilder:
    """Fluent builder for CartItem child entities."""

    def __init__(self) -> None:
        self._id: uuid.UUID = uuid.uuid4()
        self._sku_id: uuid.UUID = uuid.uuid4()
        self._product_id: uuid.UUID = uuid.uuid4()
        self._variant_id: uuid.UUID = uuid.uuid4()
        self._supplier_type: str = "local"
        self._quantity: int = 1
        self._added_at: datetime = datetime.now(UTC)

    def with_sku_id(self, sku_id: uuid.UUID) -> CartItemBuilder:
        self._sku_id = sku_id
        return self

    def with_product_id(self, product_id: uuid.UUID) -> CartItemBuilder:
        self._product_id = product_id
        return self

    def with_quantity(self, quantity: int) -> CartItemBuilder:
        self._quantity = quantity
        return self

    def with_supplier_type(self, supplier_type: str) -> CartItemBuilder:
        self._supplier_type = supplier_type
        return self

    def build(self) -> CartItem:
        return CartItem(
            id=self._id,
            sku_id=self._sku_id,
            product_id=self._product_id,
            variant_id=self._variant_id,
            supplier_type=self._supplier_type,
            quantity=self._quantity,
            added_at=self._added_at,
        )


class CartBuilder:
    """Fluent builder for Cart aggregate roots.

    Builds a Cart without using Cart.create() — bypasses factory-method
    invariants so tests can construct carts in any state.
    """

    def __init__(self) -> None:
        self._id: uuid.UUID = uuid.uuid4()
        self._identity_id: uuid.UUID | None = uuid.uuid4()
        self._anonymous_token: str | None = None
        self._status: CartStatus = CartStatus.ACTIVE
        self._version: int = 0
        self._frozen_until: datetime | None = None
        self._created_at: datetime = datetime.now(UTC)
        self._updated_at: datetime = datetime.now(UTC)
        self._last_repriced_at: datetime | None = None
        self._items: list[CartItem] = []

    def with_id(self, cart_id: uuid.UUID) -> CartBuilder:
        self._id = cart_id
        return self

    def with_identity(self, identity_id: uuid.UUID) -> CartBuilder:
        self._identity_id = identity_id
        self._anonymous_token = None
        return self

    def as_guest(self, token: str = "guest-token") -> CartBuilder:
        self._identity_id = None
        self._anonymous_token = token
        return self

    def with_status(self, status: CartStatus) -> CartBuilder:
        self._status = status
        return self

    def with_version(self, version: int) -> CartBuilder:
        self._version = version
        return self

    def with_frozen_until(self, dt: datetime) -> CartBuilder:
        self._frozen_until = dt
        return self

    def with_items(self, *items: CartItem) -> CartBuilder:
        self._items = list(items)
        return self

    def build(self) -> Cart:
        cart = Cart(
            id=self._id,
            identity_id=self._identity_id,
            anonymous_token=self._anonymous_token,
            status=self._status,
            version=self._version,
            frozen_until=self._frozen_until,
            created_at=self._created_at,
            updated_at=self._updated_at,
            last_repriced_at=self._last_repriced_at,
            items=list(self._items),
        )
        cart.clear_domain_events()
        return cart
