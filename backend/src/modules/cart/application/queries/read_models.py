"""Read models for cart queries."""

import uuid
from dataclasses import dataclass, field


@dataclass(frozen=True)
class CartItemReadModel:
    """Single item in a cart read view."""

    item_id: uuid.UUID
    sku_id: uuid.UUID
    product_id: uuid.UUID
    variant_id: uuid.UUID
    product_name: str
    variant_label: str | None
    image_url: str | None
    unit_price_amount: int
    currency: str
    quantity: int
    line_total_amount: int
    supplier_type: str
    is_available: bool


@dataclass(frozen=True)
class CartGroupReadModel:
    """Items grouped by supplier_type."""

    supplier_type: str
    items: list[CartItemReadModel] = field(default_factory=list)
    group_total_amount: int = 0


@dataclass(frozen=True)
class CartReadModel:
    """Full cart read view with grouped items."""

    cart_id: uuid.UUID
    status: str
    groups: list[CartGroupReadModel] = field(default_factory=list)
    total_amount: int = 0
    currency: str = "RUB"
    item_count: int = 0


@dataclass(frozen=True)
class CartSummaryReadModel:
    """Lightweight cart summary (count + total)."""

    cart_id: uuid.UUID
    item_count: int
    total_amount: int
    currency: str = "RUB"
