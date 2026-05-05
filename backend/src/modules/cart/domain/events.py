"""Cart domain events.

Events are emitted by the Cart aggregate during business operations,
serialized via ``dataclasses.asdict()`` and stored atomically in the
Outbox table. They are plain (non-frozen) dataclasses but MUST be
treated as immutable after construction.

Validation and ``aggregate_id`` auto-fill come from
:class:`src.shared.interfaces.entities.ModuleDomainEvent`; this module
only declares the ``aggregate_type`` discriminator and the concrete
event payloads.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime

from src.shared.interfaces.entities import ModuleDomainEvent


@dataclass
class CartEvent(ModuleDomainEvent, abstract=True):
    """Intermediate base for all cart domain events."""

    aggregate_type: str = "cart"


# ---------------------------------------------------------------------------
# Cart lifecycle events
# ---------------------------------------------------------------------------


@dataclass
class CartCreatedEvent(
    CartEvent,
    required_fields=("cart_id",),
    aggregate_id_field="cart_id",
):
    """Emitted when a new cart is created."""

    cart_id: uuid.UUID | None = None
    identity_id: uuid.UUID | None = None
    anonymous_token: str | None = None
    event_type: str = "CartCreatedEvent"


@dataclass
class CartClearedEvent(
    CartEvent,
    required_fields=("cart_id",),
    aggregate_id_field="cart_id",
):
    """Emitted when all items are removed from the cart."""

    cart_id: uuid.UUID | None = None
    event_type: str = "CartClearedEvent"


# ---------------------------------------------------------------------------
# Cart item events
# ---------------------------------------------------------------------------


@dataclass
class CartItemAddedEvent(
    CartEvent,
    required_fields=("cart_id", "item_id", "sku_id"),
    aggregate_id_field="cart_id",
):
    """Emitted when an item is added to the cart."""

    cart_id: uuid.UUID | None = None
    item_id: uuid.UUID | None = None
    sku_id: uuid.UUID | None = None
    quantity: int = 0
    event_type: str = "CartItemAddedEvent"


@dataclass
class CartItemRemovedEvent(
    CartEvent,
    required_fields=("cart_id", "item_id", "sku_id"),
    aggregate_id_field="cart_id",
):
    """Emitted when an item is removed from the cart."""

    cart_id: uuid.UUID | None = None
    item_id: uuid.UUID | None = None
    sku_id: uuid.UUID | None = None
    event_type: str = "CartItemRemovedEvent"


@dataclass
class CartItemQuantityUpdatedEvent(
    CartEvent,
    required_fields=("cart_id", "item_id"),
    aggregate_id_field="cart_id",
):
    """Emitted when an item's quantity is changed."""

    cart_id: uuid.UUID | None = None
    item_id: uuid.UUID | None = None
    old_quantity: int = 0
    new_quantity: int = 0
    event_type: str = "CartItemQuantityUpdatedEvent"


# ---------------------------------------------------------------------------
# Checkout events
# ---------------------------------------------------------------------------


@dataclass
class CartFrozenEvent(
    CartEvent,
    required_fields=("cart_id", "snapshot_id"),
    aggregate_id_field="cart_id",
):
    """Emitted when checkout is initiated (cart frozen)."""

    cart_id: uuid.UUID | None = None
    snapshot_id: uuid.UUID | None = None
    expires_at: datetime | None = None
    event_type: str = "CartFrozenEvent"


@dataclass
class CartUnfrozenEvent(
    CartEvent,
    required_fields=("cart_id",),
    aggregate_id_field="cart_id",
):
    """Emitted when checkout is cancelled or expires."""

    cart_id: uuid.UUID | None = None
    reason: str = ""
    event_type: str = "CartUnfrozenEvent"


@dataclass
class CartOrderedEvent(
    CartEvent,
    required_fields=("cart_id",),
    aggregate_id_field="cart_id",
):
    """Emitted when checkout is confirmed and cart transitions to ORDERED."""

    cart_id: uuid.UUID | None = None
    identity_id: uuid.UUID | None = None
    item_count: int = 0
    event_type: str = "CartOrderedEvent"


# ---------------------------------------------------------------------------
# Merge events
# ---------------------------------------------------------------------------


@dataclass
class CartMergedEvent(
    CartEvent,
    required_fields=("target_cart_id", "source_cart_id"),
    aggregate_id_field="target_cart_id",
):
    """Emitted when a guest cart is merged into an authenticated cart."""

    target_cart_id: uuid.UUID | None = None
    source_cart_id: uuid.UUID | None = None
    items_transferred: int = 0
    event_type: str = "CartMergedEvent"
