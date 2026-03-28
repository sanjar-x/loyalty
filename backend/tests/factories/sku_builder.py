# tests/factories/sku_builder.py
"""Fluent Builder for the SKU child entity.

SKU does NOT have a standalone create() method -- it is always created
via Product.add_sku(). This builder works differently: it requires a
Product aggregate and calls product.add_sku() internally.

NOTE: This builder mutates the parent Product aggregate (adds SKU to it).
Tests should keep a reference to the product if needed.
"""

from __future__ import annotations

import uuid

from src.modules.catalog.domain.entities import Product, SKU
from src.modules.catalog.domain.value_objects import Money


class SKUBuilder:
    """Fluent builder for SKU entities via Product.add_sku().

    Usage:
        sku = SKUBuilder().build()  # creates a default product internally
        sku = SKUBuilder().for_product(product).for_variant(variant.id).build()
    """

    def __init__(self) -> None:
        self._product: Product | None = None
        self._variant_id: uuid.UUID | None = None
        self._sku_code: str | None = None
        self._price: Money | None = None
        self._compare_at_price: Money | None = None
        self._is_active: bool = True
        self._variant_attributes: list[tuple[uuid.UUID, uuid.UUID]] = []

    def for_product(self, product: Product) -> SKUBuilder:
        self._product = product
        return self

    def for_variant(self, variant_id: uuid.UUID) -> SKUBuilder:
        self._variant_id = variant_id
        return self

    def with_sku_code(self, sku_code: str) -> SKUBuilder:
        self._sku_code = sku_code
        return self

    def with_price(self, price: Money) -> SKUBuilder:
        self._price = price
        return self

    def with_compare_at_price(self, compare_at_price: Money) -> SKUBuilder:
        self._compare_at_price = compare_at_price
        return self

    def as_inactive(self) -> SKUBuilder:
        self._is_active = False
        return self

    def with_variant_attributes(
        self, attrs: list[tuple[uuid.UUID, uuid.UUID]]
    ) -> SKUBuilder:
        self._variant_attributes = attrs
        return self

    def build(self) -> SKU:
        """Build a SKU via Product.add_sku().

        If no product is provided, creates a default one via ProductBuilder.
        If no variant_id is provided, uses the product's first variant.
        """
        if self._product is None:
            from tests.factories.product_builder import ProductBuilder

            self._product = ProductBuilder().build()

        product = self._product
        variant_id = self._variant_id
        if variant_id is None:
            # Use the first active variant
            active_variants = [v for v in product.variants if v.deleted_at is None]
            variant_id = active_variants[0].id

        sku_code = self._sku_code or f"SKU-{uuid.uuid4().hex[:6]}"
        return product.add_sku(
            variant_id,
            sku_code=sku_code,
            price=self._price,
            compare_at_price=self._compare_at_price,
            is_active=self._is_active,
            variant_attributes=self._variant_attributes or None,
        )
