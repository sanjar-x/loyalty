# src/modules/catalog/application/queries/read_models.py
"""
Read models (DTOs) for Catalog query handlers.

These are the **canonical return types** of the CQRS read side.  They
carry no business logic -- only data shaped for specific query use
cases (admin detail views, paginated lists, storefront projections).

Architectural rules
-------------------
1. Read models live in the **application layer** and MUST NOT import
   anything from the infrastructure layer (ORM models, SQLAlchemy
   sessions, etc.).  They are plain Pydantic ``BaseModel`` subclasses
   or ``dataclass``-style DTOs.

2. Query handlers in ``application.queries`` SHOULD depend on
   read-only repository interfaces defined in ``domain.interfaces``
   (e.g. ``IProductReadRepository``, ``IStorefrontQueryService``)
   rather than injecting ``AsyncSession`` directly.  This satisfies
   the Dependency Inversion Principle and keeps the application layer
   decoupled from any specific persistence technology.

3. The concrete implementations of these query interfaces live in the
   infrastructure layer alongside the ORM models.  They are free to
   use SQLAlchemy, raw SQL, Elasticsearch, or any other data source
   and are responsible for mapping rows to the read models defined
   here.

Migration note
~~~~~~~~~~~~~~
Several existing query handlers still inject ``AsyncSession`` and
import ORM models directly.  This is a known technical-debt item
(ARCH-01 / ARCH-02).  New query handlers should follow the interface
pattern; existing ones will be migrated incrementally.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginatedReadModel(BaseModel, Generic[T]):
    """Generic paginated list read model."""

    items: list[T]
    total: int
    offset: int
    limit: int


class CategoryNode(BaseModel):
    """Recursive tree node for the category hierarchy read model."""

    id: uuid.UUID
    name: str
    slug: str
    full_slug: str
    level: int
    sort_order: int
    parent_id: uuid.UUID | None = None
    children: list[CategoryNode] = Field(default_factory=list)


class CategoryReadModel(BaseModel):
    """Read model for a single category (flat, no children)."""

    id: uuid.UUID
    name: str
    slug: str
    full_slug: str
    level: int
    sort_order: int
    parent_id: uuid.UUID | None = None


CategoryListReadModel = PaginatedReadModel[CategoryReadModel]


class BrandReadModel(BaseModel):
    """Read model for a single brand."""

    id: uuid.UUID
    name: str
    slug: str
    logo_url: str | None = None
    logo_status: str | None = None


BrandListReadModel = PaginatedReadModel[BrandReadModel]


# ---------------------------------------------------------------------------
# AttributeGroup read models
# ---------------------------------------------------------------------------


class AttributeGroupReadModel(BaseModel):
    """Read model for a single attribute group."""

    id: uuid.UUID
    code: str
    name_i18n: dict[str, str]
    sort_order: int


AttributeGroupListReadModel = PaginatedReadModel[AttributeGroupReadModel]


# ---------------------------------------------------------------------------
# Attribute read models
# ---------------------------------------------------------------------------


class AttributeReadModel(BaseModel):
    """Read model for a single attribute with all fields."""

    id: uuid.UUID
    code: str
    slug: str
    name_i18n: dict[str, str]
    description_i18n: dict[str, str]
    data_type: str
    ui_type: str
    is_dictionary: bool
    group_id: uuid.UUID | None
    level: str
    is_filterable: bool
    is_searchable: bool
    search_weight: int
    is_comparable: bool
    is_visible_on_card: bool
    is_visible_in_catalog: bool
    validation_rules: dict[str, Any] | None = None


AttributeListReadModel = PaginatedReadModel[AttributeReadModel]


# ---------------------------------------------------------------------------
# AttributeValue read models
# ---------------------------------------------------------------------------


class AttributeValueReadModel(BaseModel):
    """Read model for a single attribute value."""

    id: uuid.UUID
    attribute_id: uuid.UUID
    code: str
    slug: str
    value_i18n: dict[str, Any]
    search_aliases: list[str]
    meta_data: dict[str, Any]
    value_group: str | None = None
    sort_order: int


AttributeValueListReadModel = PaginatedReadModel[AttributeValueReadModel]


# ---------------------------------------------------------------------------
# CategoryAttributeBinding read models
# ---------------------------------------------------------------------------


class CategoryAttributeBindingReadModel(BaseModel):
    """Read model for a single category-attribute binding."""

    id: uuid.UUID
    category_id: uuid.UUID
    attribute_id: uuid.UUID
    sort_order: int
    requirement_level: str
    flag_overrides: dict[str, Any] | None = None
    filter_settings: dict[str, Any] | None = None


CategoryAttributeBindingListReadModel = PaginatedReadModel[CategoryAttributeBindingReadModel]


# ---------------------------------------------------------------------------
# Storefront read models
# ---------------------------------------------------------------------------


class StorefrontValueReadModel(BaseModel):
    """A single attribute value for storefront display."""

    id: uuid.UUID
    code: str
    slug: str
    value_i18n: dict[str, Any]
    meta_data: dict[str, Any]
    value_group: str | None = None
    sort_order: int


class StorefrontFilterAttributeReadModel(BaseModel):
    """A filterable attribute for the storefront filter panel."""

    attribute_id: uuid.UUID
    code: str
    slug: str
    name_i18n: dict[str, Any]
    data_type: str
    display_type: str
    is_dictionary: bool
    values: list[StorefrontValueReadModel]
    filter_settings: dict[str, Any] | None = None
    sort_order: int


class StorefrontFilterListReadModel(BaseModel):
    """List of filterable attributes for a category."""

    category_id: uuid.UUID
    attributes: list[StorefrontFilterAttributeReadModel]


class StorefrontCardAttributeReadModel(BaseModel):
    """A single attribute for the product card."""

    attribute_id: uuid.UUID
    code: str
    slug: str
    name_i18n: dict[str, Any]
    data_type: str
    display_type: str
    requirement_level: str
    sort_order: int


class StorefrontCardGroupReadModel(BaseModel):
    """A group of attributes for the product card."""

    group_id: uuid.UUID | None
    group_code: str | None
    group_name_i18n: dict[str, Any]
    group_sort_order: int
    attributes: list[StorefrontCardAttributeReadModel]


class StorefrontCardReadModel(BaseModel):
    """Grouped card-visible attributes for a category."""

    category_id: uuid.UUID
    groups: list[StorefrontCardGroupReadModel]


class StorefrontComparisonAttributeReadModel(BaseModel):
    """A comparable attribute for the product comparison table."""

    attribute_id: uuid.UUID
    code: str
    slug: str
    name_i18n: dict[str, Any]
    data_type: str
    display_type: str
    sort_order: int


class StorefrontComparisonReadModel(BaseModel):
    """List of comparable attributes for a category."""

    category_id: uuid.UUID
    attributes: list[StorefrontComparisonAttributeReadModel]


class StorefrontFormAttributeReadModel(BaseModel):
    """A single attribute for the product creation form."""

    attribute_id: uuid.UUID
    code: str
    slug: str
    name_i18n: dict[str, Any]
    description_i18n: dict[str, Any]
    data_type: str
    display_type: str
    is_dictionary: bool
    level: str
    requirement_level: str
    validation_rules: dict[str, Any] | None = None
    values: list[StorefrontValueReadModel]
    sort_order: int


class StorefrontFormGroupReadModel(BaseModel):
    """A group of attributes for the product creation form."""

    group_id: uuid.UUID | None
    group_code: str | None
    group_name_i18n: dict[str, Any]
    group_sort_order: int
    attributes: list[StorefrontFormAttributeReadModel]


class StorefrontFormReadModel(BaseModel):
    """Complete attribute set for a product creation form, grouped."""

    category_id: uuid.UUID
    groups: list[StorefrontFormGroupReadModel]


# ---------------------------------------------------------------------------
# Product read models
# ---------------------------------------------------------------------------


class MoneyReadModel(BaseModel):
    """Read model for a monetary value.

    Represents an amount in the smallest currency unit (e.g. cents for USD)
    together with the ISO 4217 currency code.
    """

    amount: int
    currency: str


class VariantAttributePairReadModel(BaseModel):
    """A single variant attribute pair (attribute + value) on a SKU."""

    attribute_id: uuid.UUID
    attribute_value_id: uuid.UUID


class SKUReadModel(BaseModel):
    """Read model for a single SKU (product variant).

    Includes price as a nested MoneyReadModel and the list of variant
    attribute pairs that uniquely identify this variant combination.
    """

    id: uuid.UUID
    product_id: uuid.UUID
    variant_id: uuid.UUID
    sku_code: str
    variant_hash: str
    price: MoneyReadModel | None = None
    resolved_price: MoneyReadModel | None = None
    compare_at_price: MoneyReadModel | None = None
    is_active: bool
    version: int
    deleted_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    variant_attributes: list[VariantAttributePairReadModel]


def resolve_sku_price(
    sku_price: MoneyReadModel | None,
    variant_default: MoneyReadModel | None,
) -> MoneyReadModel | None:
    """Resolve effective SKU price: SKU override -> variant default -> None."""
    if sku_price is not None:
        return sku_price
    if variant_default is not None:
        return variant_default
    return None


class ProductVariantReadModel(BaseModel):
    """Read model for a single product variant with nested SKUs."""

    id: uuid.UUID
    product_id: uuid.UUID
    name_i18n: dict[str, str]
    description_i18n: dict[str, str] | None
    sort_order: int
    default_price: MoneyReadModel | None
    skus: list[SKUReadModel]


class ProductAttributeValueReadModel(BaseModel):
    """Read model for a product-attribute assignment (EAV pivot record)."""

    id: uuid.UUID
    product_id: uuid.UUID
    attribute_id: uuid.UUID
    attribute_value_id: uuid.UUID
    attribute_code: str = ""
    attribute_name_i18n: dict[str, str] = Field(default_factory=dict)


class ProductReadModel(BaseModel):
    """Full read model for a single product with nested variants and attributes.

    ``status`` is stored as a plain string (the enum value) to avoid
    importing domain types into the application read-side.
    ``min_price`` / ``max_price`` are computed aggregations across active
    SKUs and stored as plain integers (smallest currency unit).
    """

    id: uuid.UUID
    slug: str
    title_i18n: dict[str, str]
    description_i18n: dict[str, str]
    status: str
    brand_id: uuid.UUID
    primary_category_id: uuid.UUID
    supplier_id: uuid.UUID | None = None
    country_of_origin: str | None = None
    tags: list[str]
    version: int
    deleted_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    published_at: datetime | None = None
    min_price: int | None = None
    max_price: int | None = None
    price_currency: str | None = None
    variants: list[ProductVariantReadModel]
    attributes: list[ProductAttributeValueReadModel]


class ProductListItemReadModel(BaseModel):
    """Lightweight read model for product list items (admin list view).

    Contains only the fields needed for rendering a list row; omits
    heavy nested collections (``skus``, ``attributes``) for performance.
    """

    id: uuid.UUID
    slug: str
    title_i18n: dict[str, str]
    status: str
    brand_id: uuid.UUID
    primary_category_id: uuid.UUID
    version: int
    created_at: datetime
    updated_at: datetime


ProductListReadModel = PaginatedReadModel[ProductListItemReadModel]


# ---------------------------------------------------------------------------
# Product attribute (with joined attribute metadata) read models
# ---------------------------------------------------------------------------


ProductAttributeListReadModel = PaginatedReadModel[ProductAttributeValueReadModel]


SKUListReadModel = PaginatedReadModel[SKUReadModel]


VariantListReadModel = PaginatedReadModel[ProductVariantReadModel]


class MediaAssetReadModel(BaseModel):
    """Read model for a media asset."""

    id: uuid.UUID
    product_id: uuid.UUID
    variant_id: uuid.UUID | None = None
    media_type: str
    role: str
    sort_order: int
    processing_status: str | None = None
    public_url: str | None = None
    is_external: bool
    external_url: str | None = None


MediaAssetListReadModel = PaginatedReadModel[MediaAssetReadModel]


class ProductAttributeReadModel(ProductAttributeValueReadModel):
    """Read model for a product's attribute assignment with joined attribute data.

    Extends :class:`ProductAttributeValueReadModel` with attribute metadata
    (code and display name) obtained via a join, used when the consumer
    needs human-readable attribute information alongside the assignment.
    """

    attribute_code: str
    attribute_name_i18n: dict[str, str]
