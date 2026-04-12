"""
Cart aggregate root and child entities.

Part of the domain layer -- zero infrastructure imports.
"""

import uuid
from datetime import UTC, datetime, timedelta
from typing import ClassVar

from attr import dataclass, field

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
from src.modules.cart.domain.exceptions import (
    CartEmptyError,
    CartFrozenForCheckoutError,
    CartItemLimitExceededError,
    CartItemNotFoundError,
    CartItemQuantityError,
    CartNotActiveError,
    SkuNotAvailableError,
)
from src.modules.cart.domain.value_objects import (
    CartStatus,
    CheckoutSnapshot,
    SkuSnapshot,
)
from src.shared.interfaces.entities import AggregateRoot

MAX_CART_ITEMS = 50
MAX_QTY_PER_ITEM = 99
CHECKOUT_TTL_MINUTES = 15


@dataclass
class CartItem:
    """Child entity within the Cart aggregate (no AggregateRoot).

    Attributes:
        id: Unique item identifier within the cart.
        sku_id: Reference to the SKU in Catalog.
        product_id: Denormalized for grouping.
        variant_id: Denormalized for display.
        supplier_type: "cross_border" | "local".
        quantity: Number of units (1..99).
        added_at: When the item was added.
    """

    id: uuid.UUID
    sku_id: uuid.UUID
    product_id: uuid.UUID
    variant_id: uuid.UUID
    supplier_type: str
    quantity: int
    added_at: datetime = field(factory=lambda: datetime.now(UTC))


@dataclass
class Cart(AggregateRoot):
    """Cart aggregate root.

    Attributes:
        id: Unique cart identifier.
        identity_id: Authenticated owner (None for guest carts).
        anonymous_token: Server-signed guest token (None for auth carts).
        status: Current lifecycle state.
        version: Optimistic locking counter.
        frozen_until: Checkout freeze expiration, or None.
        created_at: Creation timestamp.
        updated_at: Last modification timestamp.
        last_repriced_at: Last price revalidation timestamp, or None.
        items: Child CartItem entities.
    """

    _ALLOWED_TRANSITIONS: ClassVar[dict[CartStatus, set[CartStatus]]] = {
        CartStatus.ACTIVE: {CartStatus.FROZEN, CartStatus.MERGED},
        CartStatus.FROZEN: {CartStatus.ACTIVE, CartStatus.ORDERED},
        CartStatus.MERGED: set(),
        CartStatus.ORDERED: set(),
    }

    id: uuid.UUID
    identity_id: uuid.UUID | None
    anonymous_token: str | None
    status: CartStatus
    version: int
    frozen_until: datetime | None
    created_at: datetime
    updated_at: datetime
    last_repriced_at: datetime | None
    items: list[CartItem] = field(factory=list)

    @classmethod
    def create(
        cls,
        identity_id: uuid.UUID | None = None,
        anonymous_token: str | None = None,
    ) -> Cart:
        """Factory method — preferred over direct construction."""
        if identity_id is None and anonymous_token is None:
            msg = "Cart must have either identity_id or anonymous_token"
            raise ValueError(msg)
        if identity_id is not None and anonymous_token is not None:
            msg = "Cart cannot have both identity_id and anonymous_token"
            raise ValueError(msg)
        now = datetime.now(UTC)
        cart = cls(
            id=uuid.uuid4(),
            identity_id=identity_id,
            anonymous_token=anonymous_token,
            status=CartStatus.ACTIVE,
            version=0,
            frozen_until=None,
            created_at=now,
            updated_at=now,
            last_repriced_at=None,
        )
        cart.add_domain_event(
            CartCreatedEvent(
                cart_id=cart.id,
                identity_id=identity_id,
                anonymous_token=anonymous_token,
            )
        )
        return cart

    # ---------------------------------------------------------------------------
    # Guard helpers
    # ---------------------------------------------------------------------------

    def _ensure_active(self) -> None:
        if self.status != CartStatus.ACTIVE:
            raise CartNotActiveError(status=self.status.value)

    def _touch(self) -> None:
        self.updated_at = datetime.now(UTC)

    def _find_item(self, item_id: uuid.UUID) -> CartItem:
        for item in self.items:
            if item.id == item_id:
                return item
        raise CartItemNotFoundError(item_id=str(item_id))

    def find_item_by_sku(self, sku_id: uuid.UUID) -> CartItem | None:
        for item in self.items:
            if item.sku_id == sku_id:
                return item
        return None

    # ---------------------------------------------------------------------------
    # Domain methods
    # ---------------------------------------------------------------------------

    def add_item(self, sku_snapshot: SkuSnapshot, quantity: int) -> CartItem:
        """Add an item or increment quantity if SKU already in cart."""
        self._ensure_active()

        if quantity < 1 or quantity > MAX_QTY_PER_ITEM:
            raise CartItemQuantityError(quantity=quantity)

        if not sku_snapshot.is_active:
            raise SkuNotAvailableError(sku_id=str(sku_snapshot.sku_id))

        existing = self.find_item_by_sku(sku_snapshot.sku_id)
        if existing is not None:
            new_quantity = min(existing.quantity + quantity, MAX_QTY_PER_ITEM)
            old_quantity = existing.quantity
            existing.quantity = new_quantity
            self._touch()
            self.add_domain_event(
                CartItemQuantityUpdatedEvent(
                    cart_id=self.id,
                    item_id=existing.id,
                    old_quantity=old_quantity,
                    new_quantity=new_quantity,
                )
            )
            return existing

        if len(self.items) >= MAX_CART_ITEMS:
            raise CartItemLimitExceededError(
                current=len(self.items), max_count=MAX_CART_ITEMS
            )

        item = CartItem(
            id=uuid.uuid4(),
            sku_id=sku_snapshot.sku_id,
            product_id=sku_snapshot.product_id,
            variant_id=sku_snapshot.variant_id,
            supplier_type=sku_snapshot.supplier_type,
            quantity=quantity,
        )
        self.items.append(item)
        self._touch()
        self.add_domain_event(
            CartItemAddedEvent(
                cart_id=self.id,
                item_id=item.id,
                sku_id=item.sku_id,
                quantity=quantity,
            )
        )
        return item

    def remove_item(self, item_id: uuid.UUID) -> None:
        """Remove an item from the cart."""
        self._ensure_active()
        item = self._find_item(item_id)
        self.items.remove(item)
        self._touch()
        self.add_domain_event(
            CartItemRemovedEvent(
                cart_id=self.id,
                item_id=item.id,
                sku_id=item.sku_id,
            )
        )

    def update_quantity(self, item_id: uuid.UUID, quantity: int) -> None:
        """Update item quantity. Quantity of 0 removes the item."""
        self._ensure_active()

        if quantity == 0:
            self.remove_item(item_id)
            return

        if quantity < 0 or quantity > MAX_QTY_PER_ITEM:
            raise CartItemQuantityError(quantity=quantity)

        item = self._find_item(item_id)
        old_quantity = item.quantity
        item.quantity = quantity
        self._touch()
        self.add_domain_event(
            CartItemQuantityUpdatedEvent(
                cart_id=self.id,
                item_id=item.id,
                old_quantity=old_quantity,
                new_quantity=quantity,
            )
        )

    def clear(self) -> None:
        """Remove all items from the cart."""
        self._ensure_active()
        self.items.clear()
        self._touch()
        self.add_domain_event(
            CartClearedEvent(
                cart_id=self.id,
            )
        )

    def freeze_for_checkout(
        self,
        snapshot: CheckoutSnapshot,
        expires_at: datetime,
    ) -> None:
        """Freeze cart for checkout. Transitions ACTIVE → FROZEN."""
        self._ensure_active()
        if not self.items:
            raise CartEmptyError()
        self.status = CartStatus.FROZEN
        self.frozen_until = expires_at
        self._touch()
        self.add_domain_event(
            CartFrozenEvent(
                cart_id=self.id,
                snapshot_id=snapshot.id,
                expires_at=expires_at,
            )
        )

    def unfreeze(self, reason: str = "cancelled") -> None:
        """Unfreeze cart. Transitions FROZEN → ACTIVE."""
        if self.status != CartStatus.FROZEN:
            raise CartNotActiveError(status=self.status.value)
        self.status = CartStatus.ACTIVE
        self.frozen_until = None
        self._touch()
        self.add_domain_event(
            CartUnfrozenEvent(
                cart_id=self.id,
                reason=reason,
            )
        )

    def mark_ordered(self) -> None:
        """Mark cart as ordered. Transitions FROZEN → ORDERED."""
        if self.status != CartStatus.FROZEN:
            raise CartNotActiveError(status=self.status.value)
        self.status = CartStatus.ORDERED
        self._touch()
        self.add_domain_event(
            CartOrderedEvent(
                cart_id=self.id,
                identity_id=self.identity_id,
                item_count=len(self.items),
            )
        )

    def merge_from(self, source: Cart) -> tuple[int, list[uuid.UUID]]:
        """Merge items from source cart into this cart.

        Returns:
            Tuple of (items_transferred, skipped_sku_ids).
        """
        self._ensure_active()
        if source.status == CartStatus.FROZEN:
            raise CartFrozenForCheckoutError()

        transferred = 0
        skipped: list[uuid.UUID] = []

        for src_item in source.items:
            existing = self.find_item_by_sku(src_item.sku_id)
            if existing is not None:
                existing.quantity = min(
                    existing.quantity + src_item.quantity, MAX_QTY_PER_ITEM
                )
                transferred += 1
            elif len(self.items) < MAX_CART_ITEMS:
                new_item = CartItem(
                    id=uuid.uuid4(),
                    sku_id=src_item.sku_id,
                    product_id=src_item.product_id,
                    variant_id=src_item.variant_id,
                    supplier_type=src_item.supplier_type,
                    quantity=src_item.quantity,
                )
                self.items.append(new_item)
                transferred += 1
            else:
                skipped.append(src_item.sku_id)

        source.status = CartStatus.MERGED
        source.updated_at = datetime.now(UTC)

        self._touch()
        self.add_domain_event(
            CartMergedEvent(
                target_cart_id=self.id,
                source_cart_id=source.id,
                items_transferred=transferred,
            )
        )
        return transferred, skipped

    def assign_owner(self, identity_id: uuid.UUID) -> None:
        """Reassign a guest cart to an authenticated user."""
        self._ensure_active()
        self.identity_id = identity_id
        self.anonymous_token = None
        self._touch()

    def is_freeze_expired(self) -> bool:
        """Check if the checkout freeze has expired."""
        if self.status != CartStatus.FROZEN or self.frozen_until is None:
            return False
        return datetime.now(UTC) > self.frozen_until

    def is_price_stale(self, ttl_minutes: int = 60) -> bool:
        """Check if prices should be revalidated."""
        if self.last_repriced_at is None:
            return True
        return datetime.now(UTC) > self.last_repriced_at + timedelta(
            minutes=ttl_minutes
        )
