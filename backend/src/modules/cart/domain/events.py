"""
Cart domain events.

Events are emitted by Cart aggregate during business operations, serialized
to JSON via ``dataclasses.asdict()``, and stored atomically in the Outbox table.

Events are plain (non-frozen) dataclasses because ``DomainEvent`` base class
is non-frozen. Events MUST be treated as immutable after construction.

Follows the same ``__init_subclass__`` + ``__post_init__`` validation pattern
established by ``CatalogEvent``.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import ClassVar

from src.shared.interfaces.entities import DomainEvent


@dataclass
class CartEvent(DomainEvent):
    """Intermediate base for all cart domain events.

    Subclasses declare which UUID fields are required and which field
    supplies the ``aggregate_id`` via class-level kwargs:

    * ``required_fields`` — field names that must not be ``None``.
    * ``aggregate_id_field`` — the single field whose ``str()`` value
      is copied into ``aggregate_id`` when the caller does not set it
      explicitly.
    """

    _required_fields: ClassVar[tuple[str, ...]] = ()
    _aggregate_id_field: ClassVar[str] = ""

    aggregate_type: str = "cart"
    event_type: str = "CartEvent"

    def __init_subclass__(
        cls,
        *,
        required_fields: tuple[str, ...] | None = None,
        aggregate_id_field: str | None = None,
        **kwargs: object,
    ) -> None:
        super().__init_subclass__(**kwargs)
        if required_fields is not None:
            cls._required_fields = required_fields
        if aggregate_id_field is not None:
            cls._aggregate_id_field = aggregate_id_field

        if required_fields is not None and cls.event_type == "CartEvent":
            raise TypeError(
                f"{cls.__name__} must define its own 'event_type' "
                f"(inherited default 'CartEvent' would misroute events)"
            )

    def __post_init__(self) -> None:
        cls_name = type(self).__name__
        for field_name in self._required_fields:
            if getattr(self, field_name) is None:
                raise ValueError(f"{field_name} is required for {cls_name}")
        if not self.aggregate_id and self._aggregate_id_field:
            self.aggregate_id = str(getattr(self, self._aggregate_id_field))


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
