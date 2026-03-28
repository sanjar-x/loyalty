# tests/factories/brand_builder.py
"""Fluent Builder for the Brand domain entity."""

from __future__ import annotations

import uuid

from src.modules.catalog.domain.entities import Brand


class BrandBuilder:
    """Fluent builder for Brand entities with sensible defaults.

    Usage:
        brand = BrandBuilder().build()
        brand = BrandBuilder().with_name("Nike").with_slug("nike").build()
    """

    def __init__(self) -> None:
        self._name: str = "Test Brand"
        self._slug: str | None = None
        self._logo_url: str | None = None
        self._logo_storage_object_id: uuid.UUID | None = None

    def with_name(self, name: str) -> BrandBuilder:
        self._name = name
        return self

    def with_slug(self, slug: str) -> BrandBuilder:
        self._slug = slug
        return self

    def with_logo(
        self,
        url: str,
        storage_object_id: uuid.UUID | None = None,
    ) -> BrandBuilder:
        self._logo_url = url
        self._logo_storage_object_id = storage_object_id
        return self

    def build(self) -> Brand:
        """Build a Brand via Brand.create() factory method."""
        slug = self._slug or f"brand-{uuid.uuid4().hex[:6]}"
        return Brand.create(
            name=self._name,
            slug=slug,
            logo_url=self._logo_url,
            logo_storage_object_id=self._logo_storage_object_id,
        )
