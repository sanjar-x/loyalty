# tests/factories/variant_builder.py
"""Fluent Builder for the ProductVariant child entity.

ProductVariant HAS its own create() classmethod, so the builder
calls it directly for standalone unit tests.
"""

from __future__ import annotations

import uuid

from src.modules.catalog.domain.entities import ProductVariant
from src.modules.catalog.domain.value_objects import DEFAULT_CURRENCY, Money


class ProductVariantBuilder:
    """Fluent builder for ProductVariant entities with sensible defaults.

    Usage:
        variant = ProductVariantBuilder().build()
        variant = (
            ProductVariantBuilder()
            .with_product_id(product.id)
            .with_name_i18n({"en": "Red", "ru": "Красный"})
            .build()
        )
    """

    def __init__(self) -> None:
        self._product_id: uuid.UUID | None = None
        self._name_i18n: dict[str, str] = {
            "en": "Default Variant",
            "ru": "Вариант по умолчанию",
        }
        self._description_i18n: dict[str, str] | None = None
        self._sort_order: int = 0
        self._default_price: Money | None = None
        self._default_currency: str = DEFAULT_CURRENCY

    def with_product_id(self, product_id: uuid.UUID) -> ProductVariantBuilder:
        self._product_id = product_id
        return self

    def with_name_i18n(self, name_i18n: dict[str, str]) -> ProductVariantBuilder:
        self._name_i18n = name_i18n
        return self

    def with_sort_order(self, sort_order: int) -> ProductVariantBuilder:
        self._sort_order = sort_order
        return self

    def with_price(self, price: Money) -> ProductVariantBuilder:
        self._default_price = price
        return self

    def with_currency(self, currency: str) -> ProductVariantBuilder:
        self._default_currency = currency
        return self

    def build(self) -> ProductVariant:
        """Build a ProductVariant via ProductVariant.create() factory method."""
        product_id = self._product_id or uuid.uuid4()
        return ProductVariant.create(
            product_id=product_id,
            name_i18n=self._name_i18n,
            description_i18n=self._description_i18n,
            sort_order=self._sort_order,
            default_price=self._default_price,
            default_currency=self._default_currency,
        )
