"""
Cart domain value objects.

Contains immutable types that represent domain concepts without
identity. Part of the domain layer -- zero infrastructure imports.
"""

import enum
import uuid
from datetime import datetime

from attrs import frozen


class CartStatus(enum.StrEnum):
    """Lifecycle states for a shopping cart.

    FSM transitions::

        ACTIVE -> FROZEN (freeze_for_checkout)
        ACTIVE -> MERGED (merge_from — source cart)
        FROZEN -> ACTIVE (unfreeze — cancel / TTL expired / error)
        FROZEN -> ORDERED (mark_ordered)
        MERGED -> terminal
        ORDERED -> terminal
    """

    ACTIVE = "active"
    FROZEN = "frozen"
    MERGED = "merged"
    ORDERED = "ordered"


@frozen
class SkuSnapshot:
    """ACL: translated snapshot of SKU data from Catalog BC.

    Cart never works with Catalog domain entities directly — only with
    this translated minimal snapshot. This protects Cart from changes
    in the Catalog domain model.

    Attributes:
        sku_id: Unique SKU identifier.
        product_id: Parent product identifier.
        variant_id: Parent variant identifier.
        product_name: Display name of the product.
        variant_label: Human-readable variant label, or None.
        image_url: Primary image URL, or None.
        price_amount: Price in kopecks (smallest currency unit).
        currency: ISO 4217 currency code (e.g. "RUB").
        supplier_type: "cross_border" | "local" (not imported as enum).
        is_active: Whether the SKU is currently purchasable.
    """

    sku_id: uuid.UUID
    product_id: uuid.UUID
    variant_id: uuid.UUID
    product_name: str
    variant_label: str | None
    image_url: str | None
    price_amount: int
    currency: str
    supplier_type: str
    is_active: bool


@frozen
class CheckoutItemSnapshot:
    """Immutable record of a single cart item at checkout time.

    Attributes:
        sku_id: SKU that was checked out.
        quantity: Number of units.
        unit_price_amount: Price per unit in kopecks.
        currency: ISO 4217 currency code.
    """

    sku_id: uuid.UUID
    quantity: int
    unit_price_amount: int
    currency: str


@frozen
class CheckoutSnapshot:
    """Immutable price/data snapshot created at checkout initiation.

    Attributes:
        id: Unique snapshot identifier.
        cart_id: The cart this snapshot belongs to.
        items: Frozen item-level price records.
        pickup_point_id: Selected pickup point.
        total_amount: Grand total in kopecks.
        currency: ISO 4217 currency code.
        created_at: When the snapshot was created.
        expires_at: When the snapshot becomes invalid (TTL).
    """

    id: uuid.UUID
    cart_id: uuid.UUID
    items: tuple[CheckoutItemSnapshot, ...]
    pickup_point_id: uuid.UUID
    total_amount: int
    currency: str
    created_at: datetime
    expires_at: datetime
