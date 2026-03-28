"""
ProductVariant child entity owned by the Product aggregate.

A named variation grouping that owns SKUs. Each variant represents
a tab in the admin UI with its own name, media, and set of SKUs.
Part of the domain layer -- zero infrastructure imports.
"""

import uuid
from datetime import UTC, datetime
from typing import Any, ClassVar

from attr import dataclass, field

from src.modules.catalog.domain.value_objects import (
    DEFAULT_CURRENCY,
    Money,
    validate_i18n_completeness,
)

from ._common import _generate_id, _validate_i18n_values, _validate_sort_order
from .sku import SKU


@dataclass
class ProductVariant:
    """Product variant -- a named variation grouping that owns SKUs.

    Child entity of the Product aggregate. Each variant represents a
    tab in the admin UI with its own name, media, and set of SKUs.
    """

    id: uuid.UUID
    product_id: uuid.UUID
    name_i18n: dict[str, str]
    description_i18n: dict[str, str] | None
    sort_order: int
    default_price: Money | None
    default_currency: str
    _skus: list[SKU] = field(factory=list, alias="skus")
    deleted_at: datetime | None = None
    created_at: datetime = field(factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(factory=lambda: datetime.now(UTC))

    @property
    def skus(self) -> tuple[SKU, ...]:
        """Read-only view of variant SKUs. Use Product.add_sku()/remove_sku() to mutate."""
        return tuple(self._skus)

    @classmethod
    def create(
        cls,
        *,
        product_id: uuid.UUID,
        name_i18n: dict[str, str],
        description_i18n: dict[str, str] | None = None,
        sort_order: int = 0,
        default_price: Money | None = None,
        default_currency: str = DEFAULT_CURRENCY,
        variant_id: uuid.UUID | None = None,
    ) -> ProductVariant:
        """Factory method to construct a new ProductVariant.

        Args:
            product_id: UUID of the owning Product aggregate.
            name_i18n: Multilingual variant name. At least one entry required.
            description_i18n: Optional multilingual description.
            sort_order: Display ordering among sibling variants (default: 0).
            default_price: Optional default price for SKUs in this variant.
            default_currency: Default currency code (default: "RUB").
            variant_id: Optional pre-generated UUID.

        Returns:
            A new ProductVariant instance with an empty SKU list.

        Raises:
            ValueError: If name_i18n is empty.
        """
        if not name_i18n:
            raise ValueError("name_i18n must contain at least one language entry")
        _validate_i18n_values(name_i18n, "name_i18n")
        validate_i18n_completeness(name_i18n, "name_i18n")
        _validate_sort_order(sort_order, "ProductVariant")
        return cls(
            id=variant_id or _generate_id(),
            product_id=product_id,
            name_i18n=name_i18n,
            description_i18n=description_i18n,
            sort_order=sort_order,
            default_price=default_price,
            default_currency=default_currency,
            skus=[],
        )

    _UPDATABLE_FIELDS: ClassVar[frozenset[str]] = frozenset({
        "name_i18n",
        "description_i18n",
        "sort_order",
        "default_price",
        "default_currency",
    })

    def update(self, **kwargs: Any) -> None:
        """Update mutable variant fields.

        Only fields present in ``kwargs`` are applied. Pass ``None`` for
        ``description_i18n`` or ``default_price`` to clear them.

        Raises:
            TypeError: If an unknown field name is passed.
        """
        unknown = set(kwargs) - self._UPDATABLE_FIELDS
        if unknown:
            raise TypeError(f"Cannot update immutable/unknown fields: {unknown}")

        changed = False

        if "name_i18n" in kwargs:
            if not kwargs["name_i18n"]:
                raise ValueError("name_i18n must contain at least one language entry")
            _validate_i18n_values(kwargs["name_i18n"], "name_i18n")
            self.name_i18n = kwargs["name_i18n"]
            changed = True
        if "description_i18n" in kwargs:
            self.description_i18n = kwargs["description_i18n"]
            changed = True
        if "sort_order" in kwargs:
            _validate_sort_order(kwargs["sort_order"], "ProductVariant")
            self.sort_order = kwargs["sort_order"]
            changed = True
        if "default_price" in kwargs and "default_currency" in kwargs:
            price = kwargs["default_price"]
            currency = kwargs["default_currency"]
            if price is not None and currency != price.currency:
                raise ValueError(
                    f"default_currency '{currency}' conflicts with "
                    f"default_price currency '{price.currency}'"
                )
            self.default_price = price
            if price is not None:
                self.default_currency = price.currency
            else:
                if not (
                    len(currency) == 3 and currency.isascii() and currency.isupper()
                ):
                    raise ValueError(
                        "default_currency must be exactly 3 uppercase ASCII letters"
                    )
                self.default_currency = currency
            changed = True
        elif "default_price" in kwargs:
            self.default_price = kwargs["default_price"]
            if kwargs["default_price"] is not None:
                self.default_currency = kwargs["default_price"].currency
            changed = True
        elif "default_currency" in kwargs:
            currency = kwargs["default_currency"]
            if not (len(currency) == 3 and currency.isascii() and currency.isupper()):
                raise ValueError(
                    "default_currency must be exactly 3 uppercase ASCII letters"
                )
            self.default_currency = currency
            changed = True

        if changed:
            self.updated_at = datetime.now(UTC)

    def soft_delete(self) -> None:
        """Mark this variant and all its active SKUs as deleted."""
        if self.deleted_at is not None:
            return
        now = datetime.now(UTC)
        self.deleted_at = now
        self.updated_at = now
        for sku in self.skus:
            if sku.deleted_at is None:
                sku.soft_delete()
