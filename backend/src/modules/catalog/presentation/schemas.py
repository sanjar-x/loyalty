"""
Pydantic request/response schemas for the Catalog API.

All schemas inherit from :class:`CamelModel` to provide automatic
camelCase <-> snake_case field aliasing.  These DTOs belong to the
presentation layer and carry no business logic.
"""

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import ConfigDict, Field, model_validator

from src.shared.schemas import CamelModel


class LogoMetadataRequest(CamelModel):
    """Client-supplied metadata for a brand logo upload."""

    filename: str = Field(..., max_length=255)
    content_type: str = Field(..., pattern=r"^image/(jpeg|png|webp|gif|svg\+xml)$")
    size: int | None = None


class CategoryCreateRequest(CamelModel):
    """Request body for creating a new category."""

    name: str = Field(..., min_length=2, max_length=255, examples=["Sneakers"])
    slug: str = Field(
        ...,
        min_length=3,
        max_length=255,
        pattern=r"^[a-z0-9-]+$",
        examples=["sneakers"],
    )
    parent_id: uuid.UUID | None = Field(None, description="Parent category ID (optional)")
    sort_order: int = Field(0, description="Display ordering among siblings")


class CategoryCreateResponse(CamelModel):
    """Response returned after successful category creation."""

    id: uuid.UUID
    message: str


class CategoryTreeResponse(CamelModel):
    """Recursive tree node for the category hierarchy response."""

    id: uuid.UUID
    name: str
    slug: str
    full_slug: str
    level: int
    sort_order: int
    children: list[CategoryTreeResponse]

    model_config = ConfigDict(from_attributes=True)


class CategoryResponse(CamelModel):
    """Single category detail response."""

    id: uuid.UUID
    name: str
    slug: str
    full_slug: str
    level: int
    sort_order: int
    parent_id: uuid.UUID | None = None


class CategoryUpdateRequest(CamelModel):
    """Partial update request -- all fields optional (PATCH semantics)."""

    name: str | None = Field(None, min_length=2, max_length=255)
    slug: str | None = Field(None, min_length=3, max_length=255, pattern=r"^[a-z0-9-]+$")
    sort_order: int | None = None

    @model_validator(mode="after")
    def at_least_one_field(self) -> CategoryUpdateRequest:
        if self.name is None and self.slug is None and self.sort_order is None:
            raise ValueError("At least one field (name, slug, or sortOrder) must be provided")
        return self


class CategoryListResponse(CamelModel):
    """Paginated category list response."""

    items: list[CategoryResponse]
    total: int
    offset: int
    limit: int


class BrandCreateRequest(CamelModel):
    """Request body for creating a new brand, with optional logo metadata."""

    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=255, pattern=r"^[a-z0-9-]+$")
    logo: LogoMetadataRequest | None = None


class BrandCreateResponse(CamelModel):
    """Response after brand creation, including an optional presigned upload URL."""

    brand_id: uuid.UUID
    presigned_upload_url: str | None = None
    object_key: str | None = None


class BrandResponse(CamelModel):
    """Brand detail response."""

    id: uuid.UUID
    name: str
    slug: str
    logo_url: str | None = None
    logo_status: str | None = None


class BrandUpdateRequest(CamelModel):
    """Partial update request -- all fields optional (PATCH semantics)."""

    name: str | None = Field(None, min_length=1, max_length=255)
    slug: str | None = Field(None, min_length=1, max_length=255, pattern=r"^[a-z0-9-]+$")

    @model_validator(mode="after")
    def at_least_one_field(self) -> BrandUpdateRequest:
        if self.name is None and self.slug is None:
            raise ValueError("At least one field (name or slug) must be provided")
        return self


class BrandListResponse(CamelModel):
    """Paginated brand list response."""

    items: list[BrandResponse]
    total: int
    offset: int
    limit: int


class LogoConfirmResponse(CamelModel):
    """Response after confirming logo upload."""

    message: str = "Logo processing request accepted"


# ---------------------------------------------------------------------------
# AttributeGroup schemas
# ---------------------------------------------------------------------------


class AttributeGroupCreateRequest(CamelModel):
    """Request body for creating a new attribute group."""

    code: str = Field(
        ...,
        min_length=1,
        max_length=100,
        pattern=r"^[a-z0-9_]+$",
        examples=["physical"],
        description="Machine-readable unique code",
    )
    name_i18n: dict[str, str] = Field(
        ...,
        min_length=1,
        examples=[{"en": "Physical Characteristics", "ru": "Физические характеристики"}],
        description="Multilingual display name (at least one language required)",
    )
    sort_order: int = Field(0, description="Display ordering among groups")


class AttributeGroupCreateResponse(CamelModel):
    """Response after attribute group creation."""

    group_id: uuid.UUID


class AttributeGroupResponse(CamelModel):
    """Single attribute group detail response."""

    id: uuid.UUID
    code: str
    name_i18n: dict[str, str]
    sort_order: int


class AttributeGroupUpdateRequest(CamelModel):
    """Partial update request -- code is immutable and cannot be changed."""

    name_i18n: dict[str, str] | None = Field(
        None,
        min_length=1,
        description="Multilingual display name (at least one language required)",
    )
    sort_order: int | None = None

    @model_validator(mode="after")
    def at_least_one_field(self) -> AttributeGroupUpdateRequest:
        if self.name_i18n is None and self.sort_order is None:
            raise ValueError("At least one field (nameI18n or sortOrder) must be provided")
        return self


class AttributeGroupListResponse(CamelModel):
    """Paginated attribute group list response."""

    items: list[AttributeGroupResponse]
    total: int
    offset: int
    limit: int


# ---------------------------------------------------------------------------
# Attribute schemas
# ---------------------------------------------------------------------------


class AttributeCreateRequest(CamelModel):
    """Request body for creating a new attribute."""

    code: str = Field(
        ..., min_length=1, max_length=100, pattern=r"^[a-z0-9_]+$", examples=["color"]
    )
    slug: str = Field(
        ..., min_length=1, max_length=255, pattern=r"^[a-z0-9-]+$", examples=["color"]
    )
    name_i18n: dict[str, str] = Field(..., min_length=1, examples=[{"en": "Color", "ru": "Цвет"}])
    description_i18n: dict[str, str] = Field(default_factory=dict)
    data_type: Literal["string", "integer", "float", "boolean"] = Field(..., examples=["string"])
    ui_type: Literal["text_button", "color_swatch", "dropdown", "checkbox", "range_slider"] = Field(
        ..., examples=["color_swatch"]
    )
    is_dictionary: bool = True
    group_id: uuid.UUID
    level: Literal["product", "variant"] = Field("product", examples=["product", "variant"])
    is_filterable: bool = False
    is_searchable: bool = False
    search_weight: int = Field(5, ge=1, le=10)
    is_comparable: bool = False
    is_visible_on_card: bool = False
    is_visible_in_catalog: bool = False
    validation_rules: dict[str, Any] | None = None


class AttributeCreateResponse(CamelModel):
    """Response after attribute creation."""

    attribute_id: uuid.UUID


class AttributeResponse(CamelModel):
    """Full attribute detail response."""

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


class AttributeUpdateRequest(CamelModel):
    """Partial update request -- code, slug, data_type are immutable."""

    name_i18n: dict[str, str] | None = Field(None, min_length=1)
    description_i18n: dict[str, str] | None = None
    ui_type: str | None = None
    group_id: uuid.UUID | None = None
    level: str | None = None
    is_filterable: bool | None = None
    is_searchable: bool | None = None
    search_weight: int | None = Field(None, ge=1, le=10)
    is_comparable: bool | None = None
    is_visible_on_card: bool | None = None
    is_visible_in_catalog: bool | None = None
    validation_rules: dict[str, Any] | None = ...  # type: ignore[assignment]

    @model_validator(mode="after")
    def at_least_one_field(self) -> AttributeUpdateRequest:
        """Ensure at least one field is provided for update."""
        fields = [
            self.name_i18n,
            self.description_i18n,
            self.ui_type,
            self.group_id,
            self.level,
            self.is_filterable,
            self.is_searchable,
            self.search_weight,
            self.is_comparable,
            self.is_visible_on_card,
            self.is_visible_in_catalog,
        ]
        sentinel_provided = self.validation_rules is not ...
        if all(f is None for f in fields) and not sentinel_provided:
            raise ValueError("At least one field must be provided for update")
        return self


class AttributeListResponse(CamelModel):
    """Paginated attribute list response."""

    items: list[AttributeResponse]
    total: int
    offset: int
    limit: int


# ---------------------------------------------------------------------------
# AttributeValue schemas
# ---------------------------------------------------------------------------


class AttributeValueCreateRequest(CamelModel):
    """Request body for adding a value to an attribute."""

    code: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-z0-9_]+$", examples=["red"])
    slug: str = Field(..., min_length=1, max_length=255, pattern=r"^[a-z0-9-]+$", examples=["red"])
    value_i18n: dict[str, str] = Field(..., min_length=1, examples=[{"en": "Red", "ru": "Красный"}])
    search_aliases: list[str] = Field(default_factory=list, examples=[["scarlet", "crimson"]])
    meta_data: dict[str, Any] = Field(default_factory=dict, examples=[{"hex": "#FF0000"}])
    value_group: str | None = Field(None, max_length=100, examples=["Warm tones"])
    sort_order: int = Field(0, description="Display ordering among values")


class AttributeValueCreateResponse(CamelModel):
    """Response after attribute value creation."""

    value_id: uuid.UUID


class AttributeValueResponse(CamelModel):
    """Full attribute value detail response."""

    id: uuid.UUID
    attribute_id: uuid.UUID
    code: str
    slug: str
    value_i18n: dict[str, str]
    search_aliases: list[str]
    meta_data: dict[str, Any]
    value_group: str | None = None
    sort_order: int


class AttributeValueUpdateRequest(CamelModel):
    """Partial update request -- code and slug are immutable."""

    value_i18n: dict[str, str] | None = Field(None, min_length=1)
    search_aliases: list[str] | None = None
    meta_data: dict[str, Any] | None = None
    value_group: str | None = ...  # type: ignore[assignment]
    sort_order: int | None = None

    @model_validator(mode="after")
    def at_least_one_field(self) -> AttributeValueUpdateRequest:
        """Ensure at least one field is provided for update."""
        fields = [
            self.value_i18n,
            self.search_aliases,
            self.meta_data,
            self.sort_order,
        ]
        sentinel_provided = self.value_group is not ...
        if all(f is None for f in fields) and not sentinel_provided:
            raise ValueError("At least one field must be provided for update")
        return self


class AttributeValueListResponse(CamelModel):
    """Paginated attribute value list response."""

    items: list[AttributeValueResponse]
    total: int
    offset: int
    limit: int


class ReorderItemRequest(CamelModel):
    """A single reorder instruction."""

    value_id: uuid.UUID
    sort_order: int


class ReorderAttributeValuesRequest(CamelModel):
    """Request body for bulk-reordering attribute values."""

    items: list[ReorderItemRequest] = Field(..., min_length=1)


# ---------------------------------------------------------------------------
# CategoryAttributeBinding schemas
# ---------------------------------------------------------------------------


class BindAttributeToCategoryRequest(CamelModel):
    """Request body for binding an attribute to a category."""

    attribute_id: uuid.UUID
    sort_order: int = Field(0, description="Display ordering within the category")
    requirement_level: Literal["required", "recommended", "optional"] = Field(
        "optional", examples=["required", "recommended", "optional"]
    )
    flag_overrides: dict[str, Any] | None = Field(
        None,
        description="Per-category behavior flag overrides",
        examples=[{"is_filterable": True, "search_weight": 8}],
    )
    filter_settings: dict[str, Any] | None = Field(
        None,
        description="Per-category filter settings",
        examples=[{"filter_type": "range", "thresholds": [0, 5000, 10000]}],
    )


class BindAttributeToCategoryResponse(CamelModel):
    """Response after binding creation."""

    binding_id: uuid.UUID


class CategoryAttributeBindingResponse(CamelModel):
    """Full binding detail response."""

    id: uuid.UUID
    category_id: uuid.UUID
    attribute_id: uuid.UUID
    sort_order: int
    requirement_level: str
    flag_overrides: dict[str, Any] | None = None
    filter_settings: dict[str, Any] | None = None


class CategoryAttributeBindingUpdateRequest(CamelModel):
    """Partial update request for a binding."""

    sort_order: int | None = None
    requirement_level: Literal["required", "recommended", "optional"] | None = None
    flag_overrides: dict[str, Any] | None = ...  # type: ignore[assignment]
    filter_settings: dict[str, Any] | None = ...  # type: ignore[assignment]

    @model_validator(mode="after")
    def at_least_one_field(self) -> CategoryAttributeBindingUpdateRequest:
        """Ensure at least one field is provided for update."""
        fields = [self.sort_order, self.requirement_level]
        sentinel_provided = [
            self.flag_overrides is not ...,
            self.filter_settings is not ...,
        ]
        if all(f is None for f in fields) and not any(sentinel_provided):
            raise ValueError("At least one field must be provided for update")
        return self


class CategoryAttributeBindingListResponse(CamelModel):
    """Paginated binding list response."""

    items: list[CategoryAttributeBindingResponse]
    total: int
    offset: int
    limit: int


class BindingReorderItemRequest(CamelModel):
    """A single binding reorder instruction."""

    binding_id: uuid.UUID
    sort_order: int


class ReorderBindingsRequest(CamelModel):
    """Request body for bulk-reordering bindings."""

    items: list[BindingReorderItemRequest] = Field(..., min_length=1)


class RequirementLevelUpdateItemRequest(CamelModel):
    """A single requirement-level update instruction."""

    binding_id: uuid.UUID
    requirement_level: Literal["required", "recommended", "optional"] = Field(
        ..., examples=["required", "recommended", "optional"]
    )


class BulkUpdateRequirementLevelsRequest(CamelModel):
    """Request body for bulk-updating requirement levels."""

    items: list[RequirementLevelUpdateItemRequest] = Field(..., min_length=1)


# ---------------------------------------------------------------------------
# Storefront schemas
# ---------------------------------------------------------------------------


class StorefrontValueResponse(CamelModel):
    """A single attribute value for storefront display."""

    id: uuid.UUID
    code: str
    slug: str
    value_i18n: dict[str, str]
    meta_data: dict[str, Any]
    value_group: str | None = None
    sort_order: int


class StorefrontFilterAttributeResponse(CamelModel):
    """A filterable attribute for the storefront filter panel."""

    attribute_id: uuid.UUID
    code: str
    slug: str
    name_i18n: dict[str, str]
    data_type: str
    display_type: str
    is_dictionary: bool
    values: list[StorefrontValueResponse]
    filter_settings: dict[str, Any] | None = None
    sort_order: int


class StorefrontFilterListResponse(CamelModel):
    """Filterable attributes for a category."""

    category_id: uuid.UUID
    attributes: list[StorefrontFilterAttributeResponse]


class StorefrontCardAttributeResponse(CamelModel):
    """A single attribute for the product card."""

    attribute_id: uuid.UUID
    code: str
    slug: str
    name_i18n: dict[str, str]
    data_type: str
    display_type: str
    requirement_level: str
    sort_order: int


class StorefrontCardGroupResponse(CamelModel):
    """A group of attributes for the product card."""

    group_id: uuid.UUID | None
    group_code: str | None
    group_name_i18n: dict[str, str]
    group_sort_order: int
    attributes: list[StorefrontCardAttributeResponse]


class StorefrontCardResponse(CamelModel):
    """Grouped card-visible attributes for a category."""

    category_id: uuid.UUID
    groups: list[StorefrontCardGroupResponse]


class StorefrontComparisonAttributeResponse(CamelModel):
    """A comparable attribute for the product comparison table."""

    attribute_id: uuid.UUID
    code: str
    slug: str
    name_i18n: dict[str, str]
    data_type: str
    display_type: str
    sort_order: int


class StorefrontComparisonResponse(CamelModel):
    """Comparable attributes for a category."""

    category_id: uuid.UUID
    attributes: list[StorefrontComparisonAttributeResponse]


class StorefrontFormAttributeResponse(CamelModel):
    """A single attribute for the product creation form."""

    attribute_id: uuid.UUID
    code: str
    slug: str
    name_i18n: dict[str, str]
    description_i18n: dict[str, str]
    data_type: str
    display_type: str
    is_dictionary: bool
    level: str
    requirement_level: str
    validation_rules: dict[str, Any] | None = None
    values: list[StorefrontValueResponse]
    sort_order: int


class StorefrontFormGroupResponse(CamelModel):
    """A group of attributes for the product creation form."""

    group_id: uuid.UUID | None
    group_code: str | None
    group_name_i18n: dict[str, str]
    group_sort_order: int
    attributes: list[StorefrontFormAttributeResponse]


class StorefrontFormResponse(CamelModel):
    """Complete attribute set for a product creation form, grouped."""

    category_id: uuid.UUID
    groups: list[StorefrontFormGroupResponse]


# ---------------------------------------------------------------------------
# Product schemas
# ---------------------------------------------------------------------------


class MoneySchema(CamelModel):
    """Monetary value with amount in smallest currency unit and ISO 4217 code."""

    amount: int = Field(..., ge=0)
    currency: str = Field(..., min_length=3, max_length=3, pattern=r"^[A-Z]{3}$")


class VariantAttributePairSchema(CamelModel):
    """A single variant attribute pair (attribute + value) identifying a SKU variant."""

    attribute_id: uuid.UUID
    attribute_value_id: uuid.UUID


class ProductCreateRequest(CamelModel):
    """Request body for creating a new product."""

    title_i18n: dict[str, str] = Field(..., min_length=1)
    slug: str = Field(
        ...,
        min_length=1,
        max_length=255,
        pattern=r"^[a-z0-9-]+$",
    )
    brand_id: uuid.UUID
    primary_category_id: uuid.UUID
    description_i18n: dict[str, str] = Field(default_factory=dict)
    supplier_id: uuid.UUID | None = None
    country_of_origin: str | None = Field(None, min_length=2, max_length=2, pattern=r"^[A-Z]{2}$")
    tags: list[str] = Field(default_factory=list)


class ProductCreateResponse(CamelModel):
    """Response returned after successful product creation."""

    id: uuid.UUID
    message: str


class ProductUpdateRequest(CamelModel):
    """Partial update request for a product -- all fields optional (PATCH semantics).

    At least one non-version field must be provided.  Nullable fields
    (``supplier_id``, ``country_of_origin``) use the ``...`` sentinel so that
    an explicit ``null`` can be distinguished from "not provided".
    """

    title_i18n: dict[str, str] | None = Field(None, min_length=1)
    slug: str | None = Field(
        None,
        min_length=1,
        max_length=255,
        pattern=r"^[a-z0-9-]+$",
    )
    description_i18n: dict[str, str] | None = None
    brand_id: uuid.UUID | None = None
    primary_category_id: uuid.UUID | None = None
    supplier_id: uuid.UUID | None = ...  # type: ignore[assignment]
    country_of_origin: str | None = Field(..., min_length=2, max_length=2, pattern=r"^[A-Z]{2}$")  # type: ignore[assignment]
    tags: list[str] | None = None
    version: int | None = None

    @model_validator(mode="after")
    def at_least_one_field(self) -> ProductUpdateRequest:
        """Ensure at least one non-version field is provided."""
        fields = [
            self.title_i18n,
            self.slug,
            self.description_i18n,
            self.brand_id,
            self.primary_category_id,
            self.tags,
        ]
        sentinel_fields_provided = [
            self.supplier_id is not ...,
            self.country_of_origin is not ...,
        ]
        if all(f is None for f in fields) and not any(sentinel_fields_provided):
            raise ValueError("At least one field besides 'version' must be provided")
        return self


class ProductStatusChangeRequest(CamelModel):
    """Request body for changing a product's status."""

    status: Literal["draft", "enriching", "ready_for_review", "published", "archived"] = Field(...)


class SKUCreateRequest(CamelModel):
    """Request body for adding a SKU (variant) to a product."""

    sku_code: str = Field(..., min_length=1, max_length=100)
    price_amount: int = Field(..., ge=0)
    price_currency: str = Field(..., min_length=3, max_length=3, pattern=r"^[A-Z]{3}$")
    compare_at_price_amount: int | None = Field(None, ge=0)
    is_active: bool = True
    variant_attributes: list[VariantAttributePairSchema] = Field(default_factory=list)


class SKUCreateResponse(CamelModel):
    """Response returned after successful SKU creation."""

    id: uuid.UUID
    message: str


class SKUUpdateRequest(CamelModel):
    """Partial update request for a SKU -- all fields optional (PATCH semantics)."""

    sku_code: str | None = Field(None, min_length=1, max_length=100)
    price_amount: int | None = Field(None, ge=0)
    price_currency: str | None = Field(None, min_length=3, max_length=3, pattern=r"^[A-Z]{3}$")
    compare_at_price_amount: int | None = ...  # type: ignore[assignment]
    is_active: bool | None = None
    variant_attributes: list[VariantAttributePairSchema] | None = None
    version: int | None = None

    @model_validator(mode="after")
    def at_least_one_field(self) -> SKUUpdateRequest:
        """Ensure at least one field is provided for update."""
        fields = [
            self.sku_code,
            self.price_amount,
            self.price_currency,
            self.is_active,
            self.variant_attributes,
        ]
        sentinel_provided = self.compare_at_price_amount is not ...
        if all(f is None for f in fields) and not sentinel_provided:
            raise ValueError("At least one field must be provided for update")
        return self


class SKUResponse(CamelModel):
    """Full SKU (variant) detail response."""

    id: uuid.UUID
    product_id: uuid.UUID
    sku_code: str
    variant_hash: str
    price: MoneySchema
    compare_at_price: MoneySchema | None = None
    is_active: bool
    version: int
    deleted_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    variant_attributes: list[VariantAttributePairSchema]


class ProductAttributeAssignRequest(CamelModel):
    """Request body for assigning an attribute value to a product."""

    attribute_id: uuid.UUID
    attribute_value_id: uuid.UUID


class ProductAttributeAssignResponse(CamelModel):
    """Response returned after successful attribute assignment."""

    id: uuid.UUID
    message: str


class ProductAttributeResponse(CamelModel):
    """Single product-attribute assignment detail response."""

    id: uuid.UUID
    product_id: uuid.UUID
    attribute_id: uuid.UUID
    attribute_value_id: uuid.UUID
    attribute_code: str = ""
    attribute_name_i18n: dict[str, str] = Field(default_factory=dict)


class ProductResponse(CamelModel):
    """Full product detail response with nested SKUs and attribute assignments."""

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
    skus: list[SKUResponse]
    attributes: list[ProductAttributeResponse]


class ProductListItemResponse(CamelModel):
    """Lightweight product item for list views (omits nested collections)."""

    id: uuid.UUID
    slug: str
    title_i18n: dict[str, str]
    status: str
    brand_id: uuid.UUID
    primary_category_id: uuid.UUID
    version: int
    created_at: datetime
    updated_at: datetime


class ProductListResponse(CamelModel):
    """Paginated product list response."""

    items: list[ProductListItemResponse]
    total: int
    offset: int
    limit: int


# ---------------------------------------------------------------------------
# Product media schemas
# ---------------------------------------------------------------------------


class ProductMediaUploadRequest(CamelModel):
    """Request body for reserving a media upload slot."""

    attribute_value_id: uuid.UUID | None = None
    media_type: str = Field(..., pattern=r"^(image|video|model_3d|document)$")
    role: str = Field(..., pattern=r"^(main|hover|gallery|hero_video|size_guide|packaging)$")
    content_type: str = Field(
        ...,
        pattern=r"^(image|video|application|model)/[a-zA-Z0-9][a-zA-Z0-9!#$&\-^_.+]*$",
        max_length=255,
    )
    sort_order: int = Field(0, ge=0)


class ProductMediaUploadResponse(CamelModel):
    """Response with presigned upload URL."""

    id: uuid.UUID
    presigned_upload_url: str
    object_key: str


class ProductMediaExternalRequest(CamelModel):
    """Request body for adding an external media URL (e.g., YouTube)."""

    attribute_value_id: uuid.UUID | None = None
    media_type: str = Field(..., pattern=r"^(image|video|model_3d|document)$")
    role: str = Field(..., pattern=r"^(main|hover|gallery|hero_video|size_guide|packaging)$")
    external_url: str = Field(..., min_length=1, max_length=2048, pattern=r"^https?://")
    sort_order: int = Field(0, ge=0)


class ProductMediaResponse(CamelModel):
    """Media asset detail response."""

    id: uuid.UUID
    product_id: uuid.UUID
    attribute_value_id: uuid.UUID | None = None
    media_type: str
    role: str
    sort_order: int
    processing_status: str | None = None
    public_url: str | None = None
    is_external: bool
    external_url: str | None = None


class MediaProcessingWebhookRequest(CamelModel):
    """Internal webhook body from AI-service after processing."""

    object_key: str = Field(..., pattern=r"^[a-zA-Z0-9/_.-]+$", max_length=1024)
    content_type: str = Field(
        ...,
        pattern=r"^[a-zA-Z0-9][a-zA-Z0-9!#$&\-^_.+]+/[a-zA-Z0-9][a-zA-Z0-9!#$&\-^_.+]+$",
        max_length=255,
    )
    size_bytes: int = Field(..., ge=0)


class MediaProcessingFailedRequest(CamelModel):
    """Internal webhook body from AI-service on failure."""

    error: str = Field(..., max_length=2000)


class WebhookAckResponse(CamelModel):
    """Acknowledgement response for internal webhooks."""

    status: str = "ok"
