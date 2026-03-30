# tests/factories/product_builder.py
"""Fluent Builder for the Product aggregate root.

NOTE: Product.create() auto-creates one default variant and emits
ProductCreatedEvent. After build(), the product always has >= 1 variant.
"""

from __future__ import annotations

import uuid

from src.modules.catalog.domain.entities import Product


class ProductBuilder:
    """Fluent builder for Product aggregates with sensible defaults.

    Usage:
        product = ProductBuilder().build()
        product = (
            ProductBuilder()
            .with_slug("nike-air-max")
            .with_brand_id(brand.id)
            .with_category_id(cat.id)
            .build()
        )
    """

    def __init__(self) -> None:
        self._slug: str | None = None
        self._title_i18n: dict[str, str] = {
            "en": "Test Product",
            "ru": "Тестовый продукт",
        }
        self._brand_id: uuid.UUID | None = None
        self._primary_category_id: uuid.UUID | None = None
        self._description_i18n: dict[str, str] = {}
        self._supplier_id: uuid.UUID | None = None
        self._source_url: str | None = None
        self._country_of_origin: str | None = None
        self._tags: list[str] = []

    def with_slug(self, slug: str) -> ProductBuilder:
        self._slug = slug
        return self

    def with_title_i18n(self, title_i18n: dict[str, str]) -> ProductBuilder:
        self._title_i18n = title_i18n
        return self

    def with_brand_id(self, brand_id: uuid.UUID) -> ProductBuilder:
        self._brand_id = brand_id
        return self

    def with_category_id(self, category_id: uuid.UUID) -> ProductBuilder:
        self._primary_category_id = category_id
        return self

    def with_description_i18n(self, description_i18n: dict[str, str]) -> ProductBuilder:
        self._description_i18n = description_i18n
        return self

    def with_supplier_id(self, supplier_id: uuid.UUID) -> ProductBuilder:
        self._supplier_id = supplier_id
        return self

    def with_source_url(self, source_url: str) -> ProductBuilder:
        self._source_url = source_url
        return self

    def with_country_of_origin(self, country_of_origin: str) -> ProductBuilder:
        self._country_of_origin = country_of_origin
        return self

    def with_tags(self, tags: list[str]) -> ProductBuilder:
        self._tags = tags
        return self

    def build(self) -> Product:
        """Build a Product via Product.create() factory method.

        Product.create() auto-creates one default variant and emits
        ProductCreatedEvent.
        """
        slug = self._slug or f"product-{uuid.uuid4().hex[:6]}"
        brand_id = self._brand_id or uuid.uuid4()
        category_id = self._primary_category_id or uuid.uuid4()
        return Product.create(
            slug=slug,
            title_i18n=self._title_i18n,
            brand_id=brand_id,
            primary_category_id=category_id,
            description_i18n=self._description_i18n or None,
            supplier_id=self._supplier_id,
            source_url=self._source_url,
            country_of_origin=self._country_of_origin,
            tags=self._tags or None,
        )
