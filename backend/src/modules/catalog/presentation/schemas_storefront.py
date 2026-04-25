"""
Pydantic response schemas for storefront (customer-facing) catalog endpoints.

All schemas inherit from :class:`CamelModel` for automatic snake_case → camelCase
serialisation.  i18n fields carry the full locale dict; projection to a single
locale happens in the router layer (same pattern as attribute storefront schemas).
"""

import uuid
from datetime import datetime
from typing import Generic, TypeVar

from pydantic import Field

from src.shared.schemas import CamelModel

S = TypeVar("S")


# ---------------------------------------------------------------------------
# Cursor-paginated response envelope
# ---------------------------------------------------------------------------


class CursorPaginatedResponse(CamelModel, Generic[S]):
    """Generic cursor-paginated list response."""

    items: list[S]
    has_next: bool = False
    next_cursor: str | None = None
    total: int | None = None


# ---------------------------------------------------------------------------
# Embedded value schemas
# ---------------------------------------------------------------------------


class StorefrontMoneyResponse(CamelModel):
    """Monetary amount for the storefront."""

    amount: int = Field(
        description="Amount in the smallest currency unit (e.g. kopecks)"
    )
    currency: str = "RUB"
    compare_at: int | None = Field(
        None, description="Original (strike-through) price before discount"
    )


class StorefrontImageResponse(CamelModel):
    """Product image with optional responsive variants."""

    url: str
    image_variants: list[dict] | None = Field(
        None,
        description=(
            "Responsive variants for the image, e.g. [{size, width, height, url}, ...]"
        ),
    )


class StorefrontBrandResponse(CamelModel):
    """Minimal brand info embedded in product cards."""

    id: uuid.UUID
    name: str
    slug: str
    logo_url: str | None = None


class StorefrontSupplierResponse(CamelModel):
    """Storefront supplier projection — exposes ``type`` only.

    Drives cross-border vs local UI/logistics branching without leaking
    the supplier's identity to public catalog consumers.
    """

    type: str = Field(
        description="SupplierType enum value: 'cross_border' or 'local'",
    )


class BreadcrumbResponse(CamelModel):
    """Single breadcrumb item (root → leaf)."""

    label_i18n: dict[str, str]
    slug: str
    label: str | None = None


# ---------------------------------------------------------------------------
# PLP — Product card
# ---------------------------------------------------------------------------


class StorefrontProductCardResponse(CamelModel):
    """Lightweight product card for PLP grids."""

    id: uuid.UUID
    slug: str
    title_i18n: dict[str, str]
    title: str | None = None
    image: StorefrontImageResponse | None = None
    images: list[StorefrontImageResponse] = Field(default_factory=list)
    price: StorefrontMoneyResponse | None = None
    brand: StorefrontBrandResponse | None = None
    supplier: StorefrontSupplierResponse | None = None
    popularity_score: int = 0
    published_at: datetime | None = None
    variant_count: int = 0
    in_stock: bool = False


# ---------------------------------------------------------------------------
# PDP — Full product detail
# ---------------------------------------------------------------------------


class StorefrontVariantAttributePairResponse(CamelModel):
    """Variant attribute pair (attribute + value) on a SKU."""

    attribute_id: uuid.UUID
    attribute_value_id: uuid.UUID


class StorefrontSKUResponse(CamelModel):
    """Individual SKU within a variant."""

    id: uuid.UUID
    sku_code: str
    price: StorefrontMoneyResponse | None = None
    resolved_price: StorefrontMoneyResponse | None = None
    compare_at_price: StorefrontMoneyResponse | None = None
    is_active: bool = True
    variant_attributes: list[StorefrontVariantAttributePairResponse] = Field(
        default_factory=list
    )


class StorefrontVariantResponse(CamelModel):
    """Product variant with nested SKUs."""

    id: uuid.UUID
    name_i18n: dict[str, str]
    name: str | None = None
    sort_order: int = 0
    skus: list[StorefrontSKUResponse] = Field(default_factory=list)


class StorefrontAttributeValueResponse(CamelModel):
    """Product attribute value for PDP display."""

    attribute_code: str
    attribute_name_i18n: dict[str, str]
    attribute_name: str | None = None
    value_code: str
    value_i18n: dict[str, str]
    value: str | None = None
    group_code: str | None = None
    group_name_i18n: dict[str, str] | None = None
    group_name: str | None = None
    sort_order: int = 0


class StorefrontProductDetailResponse(CamelModel):
    """Full product detail for PDP."""

    id: uuid.UUID
    slug: str
    title_i18n: dict[str, str]
    title: str | None = None
    description_i18n: dict[str, str] = Field(default_factory=dict)
    description: str | None = None
    brand: StorefrontBrandResponse | None = None
    supplier: StorefrontSupplierResponse | None = None
    price: StorefrontMoneyResponse | None = None
    popularity_score: int = 0
    published_at: datetime | None = None
    variant_count: int = 0
    in_stock: bool = False
    media: list[StorefrontImageResponse] = Field(default_factory=list)
    variants: list[StorefrontVariantResponse] = Field(default_factory=list)
    attributes: list[StorefrontAttributeValueResponse] = Field(default_factory=list)
    breadcrumbs: list[BreadcrumbResponse] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    version: int = 1


# ---------------------------------------------------------------------------
# Facets — Filter panel response schemas (Phase 2)
# ---------------------------------------------------------------------------


class FacetValueResponse(CamelModel):
    """Single attribute value with count."""

    value_id: uuid.UUID
    code: str
    slug: str
    value_i18n: dict[str, str | None] = Field(default_factory=dict)
    meta_data: dict = Field(default_factory=dict)
    value_group: str | None = None
    sort_order: int = 0
    count: int = 0


class FacetGroupResponse(CamelModel):
    """Facet group — one filterable attribute with counted values."""

    attribute_id: uuid.UUID
    code: str
    slug: str
    name_i18n: dict[str, str | None] = Field(default_factory=dict)
    ui_type: str = "multi_select"
    selection_mode: str = "multi"
    values: list[FacetValueResponse] = Field(default_factory=list)


class BrandFacetResponse(CamelModel):
    """Brand option with count."""

    brand_id: uuid.UUID
    name: str
    slug: str
    logo_url: str | None = None
    count: int = 0


class PriceRangeResponse(CamelModel):
    """Min/max price range for the current filter set."""

    min_price: int
    max_price: int
    currency: str = "RUB"


class FacetResultResponse(CamelModel):
    """Complete facet data returned alongside PLP results."""

    attribute_facets: list[FacetGroupResponse] = Field(default_factory=list)
    brand_facets: list[BrandFacetResponse] = Field(default_factory=list)
    price_range: PriceRangeResponse | None = None
    total_products: int = 0


# ---------------------------------------------------------------------------
# PLP combined response (products + optional facets)
# ---------------------------------------------------------------------------


class StorefrontPLPResponse(CamelModel):
    """PLP response with product cards and optional facet data."""

    items: list[StorefrontProductCardResponse] = Field(default_factory=list)
    has_next: bool = False
    next_cursor: str | None = None
    total: int | None = None
    facets: FacetResultResponse | None = None


# ---------------------------------------------------------------------------
# Search suggestion response (Phase 3)
# ---------------------------------------------------------------------------


class SearchSuggestionResponse(CamelModel):
    """A single autocomplete suggestion."""

    type: str = Field(description="Suggestion type: product, category, or brand")
    text: str = Field(description="Display text")
    slug: str = Field(description="URL slug for navigation")
    extra: dict | None = Field(
        None, description="Additional data (logo_url, full_slug, etc.)"
    )
