"""
SKU child entity owned by the Product aggregate.

Stock Keeping Unit -- a purchasable item within a ProductVariant.
Each SKU represents a unique combination of variant attributes
identified by its ``variant_hash``.
Part of the domain layer -- zero infrastructure imports.
"""

import uuid
from datetime import UTC, datetime
from typing import Any, ClassVar

from attr import dataclass, field

from src.modules.catalog.domain.value_objects import Money


@dataclass
class SKU:
    """Stock Keeping Unit -- a purchasable item within a ProductVariant.

    Child entity owned by a ProductVariant (which is itself a child of
    the Product aggregate). Each SKU represents a unique combination of
    variant attributes (e.g. size) identified by its ``variant_hash``.
    The hash is computed once by the owning Product and stored immutably;
    it is recalculated only when ``variant_attributes`` change via ``update()``.

    Attributes:
        id: Unique SKU identifier.
        product_id: FK to the owning Product aggregate (denormalized).
        variant_id: FK to the parent ProductVariant.
        sku_code: Human-readable stock-keeping code.
        variant_hash: SHA-256 hash of sorted variant attribute pairs.
        price: Base price as a Money value object, or None to inherit from variant.
        compare_at_price: Previous/original price for strikethrough display.
        is_active: Whether the SKU is available for sale.
        version: Optimistic locking version counter (incremented by repo on save).
        deleted_at: Soft-delete timestamp, or None if active.
        created_at: Creation timestamp (UTC).
        updated_at: Last modification timestamp (UTC).
        variant_attributes: List of (attribute_id, attribute_value_id) tuples.
    """

    id: uuid.UUID
    product_id: uuid.UUID
    variant_id: uuid.UUID
    sku_code: str
    variant_hash: str
    price: Money | None = None
    compare_at_price: Money | None = None
    is_active: bool = True
    version: int = 1
    deleted_at: datetime | None = None
    created_at: datetime = field(factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(factory=lambda: datetime.now(UTC))
    variant_attributes: list[tuple[uuid.UUID, uuid.UUID]] = field(factory=list)

    def __attrs_post_init__(self) -> None:
        """Validate compare_at_price > price when both are provided."""
        if self.price is None and self.compare_at_price is not None:
            raise ValueError("compare_at_price cannot be set when price is None")
        if self.compare_at_price is not None:
            if self.compare_at_price.amount <= 0:
                raise ValueError("compare_at_price amount must be greater than zero")
            if self.price is not None:
                if self.compare_at_price.currency != self.price.currency:
                    raise ValueError(
                        f"compare_at_price currency ({self.compare_at_price.currency}) "
                        f"must match price currency ({self.price.currency})"
                    )
                if not self.compare_at_price > self.price:
                    raise ValueError("compare_at_price must be greater than price")

    def soft_delete(self) -> None:
        """Mark this SKU as deleted.

        Sets ``deleted_at`` and ``updated_at`` to the current UTC timestamp.
        The record is retained in the database; filters must exclude
        non-None ``deleted_at`` when listing active variants.
        """
        if self.deleted_at is not None:
            return
        now = datetime.now(UTC)
        self.deleted_at = now
        self.updated_at = now

    _UPDATABLE_FIELDS: ClassVar[frozenset[str]] = frozenset(
        {
            "sku_code",
            "price",
            "compare_at_price",
            "is_active",
        }
    )

    def update(self, **kwargs: Any) -> None:
        """Update mutable SKU fields.

        Only fields present in ``kwargs`` are applied. Pass ``None`` for
        ``compare_at_price`` to clear it.

        After any price or compare_at_price change the constraint
        ``compare_at_price > price`` is re-validated.

        Raises:
            TypeError: If an unknown field name is passed.
            ValueError: If the resulting compare_at_price <= price.
        """
        unknown = set(kwargs) - self._UPDATABLE_FIELDS
        if unknown:
            raise TypeError(f"Cannot update immutable/unknown fields: {unknown}")

        # Validate-then-mutate: compute new state before touching self
        new_price = kwargs["price"] if "price" in kwargs else self.price
        new_compare = (
            kwargs["compare_at_price"]
            if "compare_at_price" in kwargs
            else self.compare_at_price
        )

        if new_price is None and new_compare is not None:
            raise ValueError("compare_at_price cannot be set when price is None")
        if new_compare is not None:
            if new_compare.amount <= 0:
                raise ValueError("compare_at_price amount must be greater than zero")
            if new_price is not None:
                if new_compare.currency != new_price.currency:
                    raise ValueError(
                        f"compare_at_price currency ({new_compare.currency}) "
                        f"must match price currency ({new_price.currency})"
                    )
                if not new_compare > new_price:
                    raise ValueError("compare_at_price must be greater than price")

        # All validation passed — safe to mutate
        changed = False
        if "sku_code" in kwargs:
            self.sku_code = kwargs["sku_code"]
            changed = True
        if "price" in kwargs:
            self.price = kwargs["price"]
            changed = True
        if "compare_at_price" in kwargs:
            self.compare_at_price = kwargs["compare_at_price"]
            changed = True
        if "is_active" in kwargs:
            self.is_active = kwargs["is_active"]
            changed = True

        if changed:
            self.updated_at = datetime.now(UTC)
