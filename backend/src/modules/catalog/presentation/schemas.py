"""
Pydantic request/response schemas for the Catalog API.

All schemas inherit from :class:`CamelModel` to provide automatic
camelCase <-> snake_case field aliasing.  These DTOs belong to the
presentation layer and carry no business logic.
"""

import json
import re
import uuid
from datetime import datetime
from typing import Annotated, Any, Generic, Literal, TypeVar

from pydantic import AfterValidator, ConfigDict, Field, model_validator

from src.shared.schemas import CamelModel

S = TypeVar("S")


class PaginatedResponse(CamelModel, Generic[S]):
    """Generic paginated list response with camelCase serialization."""

    items: list[S]
    total: int
    offset: int
    limit: int


# ---------------------------------------------------------------------------
# i18n language code validation
# ---------------------------------------------------------------------------

# ISO 639-1 two-letter language codes (lowercase).
_LANG_CODE_RE = re.compile(r"^[a-z]{2}$")


def _validate_i18n_keys(value: dict[str, str]) -> dict[str, str]:
    """Validate that all keys in an i18n dict are ISO 639-1 language codes."""
    for key in value:
        if not _LANG_CODE_RE.match(key):
            raise ValueError(
                f"Invalid language code '{key}'. "
                f"Keys must be ISO 639-1 two-letter lowercase codes (e.g. 'en', 'ru')."
            )
    return value


I18nDict = Annotated[dict[str, str], AfterValidator(_validate_i18n_keys)]
"""A ``dict[str, str]`` whose keys are validated as ISO 639-1 language codes."""

_MAX_JSON_DICT_BYTES = 10_240  # 10 KB
_MAX_JSON_DICT_DEPTH = 4


def _check_nesting_depth(obj: Any, current: int = 0) -> int:
    """Return the maximum nesting depth of a JSON-like object."""
    if current > _MAX_JSON_DICT_DEPTH:
        return current
    if isinstance(obj, dict):
        if not obj:
            return current
        return max(_check_nesting_depth(v, current + 1) for v in obj.values())
    if isinstance(obj, list):
        if not obj:
            return current
        return max(_check_nesting_depth(v, current + 1) for v in obj)
    return current


def _validate_bounded_json_dict(value: dict[str, Any]) -> dict[str, Any]:
    """Reject dicts that are too large or too deeply nested (JSON bomb protection)."""
    serialized_size = len(json.dumps(value, default=str))
    if serialized_size > _MAX_JSON_DICT_BYTES:
        raise ValueError(
            f"JSON object too large: {serialized_size} bytes (max {_MAX_JSON_DICT_BYTES} bytes)"
        )
    depth = _check_nesting_depth(value)
    if depth > _MAX_JSON_DICT_DEPTH:
        raise ValueError(
            f"JSON object too deeply nested: depth {depth} (max {_MAX_JSON_DICT_DEPTH})"
        )
    return value


BoundedJsonDict = Annotated[dict[str, Any], AfterValidator(_validate_bounded_json_dict)]
"""A ``dict[str, Any]`` with size (10 KB) and nesting depth (4) limits."""


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


CategoryListResponse = PaginatedResponse[CategoryResponse]


class BrandCreateRequest(CamelModel):
    """Request body for creating a new brand, with optional logo metadata."""

    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=255, pattern=r"^[a-z0-9-]+$")
    logo: LogoMetadataRequest | None = None


class BrandCreateResponse(CamelModel):
    """Response after brand creation, including an optional presigned upload URL."""

    id: uuid.UUID
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


BrandListResponse = PaginatedResponse[BrandResponse]


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
    name_i18n: I18nDict = Field(
        ...,
        min_length=1,
        examples=[{"en": "Physical Characteristics", "ru": "Физические характеристики"}],
        description="Multilingual display name (at least one language required)",
    )
    sort_order: int = Field(0, description="Display ordering among groups")


class AttributeGroupCreateResponse(CamelModel):
    """Response after attribute group creation."""

    id: uuid.UUID


class AttributeGroupResponse(CamelModel):
    """Single attribute group detail response."""

    id: uuid.UUID
    code: str
    name_i18n: dict[str, str]
    sort_order: int


class AttributeGroupUpdateRequest(CamelModel):
    """Partial update request -- code is immutable and cannot be changed."""

    name_i18n: I18nDict | None = Field(
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


AttributeGroupListResponse = PaginatedResponse[AttributeGroupResponse]


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
    name_i18n: I18nDict = Field(..., min_length=1, examples=[{"en": "Color", "ru": "Цвет"}])
    description_i18n: I18nDict = Field(default_factory=dict)
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
    validation_rules: BoundedJsonDict | None = None


class AttributeCreateResponse(CamelModel):
    """Response after attribute creation."""

    id: uuid.UUID


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

    name_i18n: I18nDict | None = Field(None, min_length=1)
    description_i18n: I18nDict | None = None
    ui_type: str | None = None
    group_id: uuid.UUID | None = None
    level: str | None = None
    is_filterable: bool | None = None
    is_searchable: bool | None = None
    search_weight: int | None = Field(None, ge=1, le=10)
    is_comparable: bool | None = None
    is_visible_on_card: bool | None = None
    is_visible_in_catalog: bool | None = None
    validation_rules: BoundedJsonDict | None = None

    @model_validator(mode="after")
    def at_least_one_field(self) -> AttributeUpdateRequest:
        """Ensure at least one field is provided for update."""
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided for update")
        return self


AttributeListResponse = PaginatedResponse[AttributeResponse]


# ---------------------------------------------------------------------------
# AttributeValue schemas
# ---------------------------------------------------------------------------


class AttributeValueCreateRequest(CamelModel):
    """Request body for adding a value to an attribute."""

    code: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-z0-9_]+$", examples=["red"])
    slug: str = Field(..., min_length=1, max_length=255, pattern=r"^[a-z0-9-]+$", examples=["red"])
    value_i18n: I18nDict = Field(..., min_length=1, examples=[{"en": "Red", "ru": "Красный"}])
    search_aliases: list[Annotated[str, Field(max_length=100)]] = Field(
        default_factory=list,
        max_length=50,
        examples=[["scarlet", "crimson"]],
        description="Search synonyms (max 50 entries, each max 100 chars)",
    )
    meta_data: BoundedJsonDict = Field(default_factory=dict, examples=[{"hex": "#FF0000"}])
    value_group: str | None = Field(None, max_length=100, examples=["Warm tones"])
    sort_order: int = Field(0, description="Display ordering among values")


class AttributeValueCreateResponse(CamelModel):
    """Response after attribute value creation."""

    id: uuid.UUID


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

    value_i18n: I18nDict | None = Field(None, min_length=1)
    search_aliases: list[Annotated[str, Field(max_length=100)]] | None = Field(None, max_length=50)
    meta_data: BoundedJsonDict | None = None
    value_group: str | None = None
    sort_order: int | None = None

    @model_validator(mode="after")
    def at_least_one_field(self) -> AttributeValueUpdateRequest:
        """Ensure at least one field is provided for update."""
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided for update")
        return self


AttributeValueListResponse = PaginatedResponse[AttributeValueResponse]


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
    flag_overrides: BoundedJsonDict | None = Field(
        None,
        description="Per-category behavior flag overrides",
        examples=[{"is_filterable": True, "search_weight": 8}],
    )
    filter_settings: BoundedJsonDict | None = Field(
        None,
        description="Per-category filter settings",
        examples=[{"filter_type": "range", "thresholds": [0, 5000, 10000]}],
    )


class BindAttributeToCategoryResponse(CamelModel):
    """Response after binding creation."""

    id: uuid.UUID


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
    flag_overrides: BoundedJsonDict | None = None
    filter_settings: BoundedJsonDict | None = None

    @model_validator(mode="after")
    def at_least_one_field(self) -> CategoryAttributeBindingUpdateRequest:
        """Ensure at least one field is provided for update."""
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided for update")
        return self


CategoryAttributeBindingListResponse = PaginatedResponse[CategoryAttributeBindingResponse]


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
    ui_type: str
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
    ui_type: str
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
    ui_type: str
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
    ui_type: str
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

    title_i18n: I18nDict = Field(..., min_length=1)
    slug: str = Field(
        ...,
        min_length=1,
        max_length=255,
        pattern=r"^[a-z0-9-]+$",
    )
    brand_id: uuid.UUID
    primary_category_id: uuid.UUID
    description_i18n: I18nDict = Field(default_factory=dict)
    supplier_id: uuid.UUID | None = None
    country_of_origin: str | None = Field(None, min_length=2, max_length=2, pattern=r"^[A-Z]{2}$")
    tags: list[str] = Field(default_factory=list)


class ProductCreateResponse(CamelModel):
    """Response returned after successful product creation."""

    id: uuid.UUID
    message: str


class ProductUpdateRequest(CamelModel):
    """Partial update request for a product -- all fields optional (PATCH semantics).

    At least one non-version field must be provided.  Uses
    ``model_fields_set`` to distinguish "not provided" from an explicit
    ``null`` for nullable fields (``supplier_id``, ``country_of_origin``).
    """

    title_i18n: I18nDict | None = Field(None, min_length=1)
    slug: str | None = Field(
        None,
        min_length=1,
        max_length=255,
        pattern=r"^[a-z0-9-]+$",
    )
    description_i18n: I18nDict | None = None
    brand_id: uuid.UUID | None = None
    primary_category_id: uuid.UUID | None = None
    supplier_id: uuid.UUID | None = None
    country_of_origin: str | None = Field(None, min_length=2, max_length=2, pattern=r"^[A-Z]{2}$")
    tags: list[str] | None = None
    version: int | None = None

    @model_validator(mode="after")
    def at_least_one_field(self) -> ProductUpdateRequest:
        """Ensure at least one non-version field is provided."""
        if not (self.model_fields_set - {"version"}):
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
    compare_at_price_amount: int | None = None
    is_active: bool | None = None
    variant_attributes: list[VariantAttributePairSchema] | None = None
    version: int | None = None

    @model_validator(mode="after")
    def at_least_one_field(self) -> SKUUpdateRequest:
        """Ensure at least one field is provided for update."""
        if not (self.model_fields_set - {"version"}):
            raise ValueError("At least one field besides 'version' must be provided")
        return self


class SKUResponse(CamelModel):
    """Full SKU detail response."""

    id: uuid.UUID
    product_id: uuid.UUID
    variant_id: uuid.UUID
    sku_code: str
    price: MoneySchema | None = None
    resolved_price: MoneySchema | None = None
    compare_at_price: MoneySchema | None = None
    is_active: bool
    version: int
    created_at: datetime
    updated_at: datetime
    variant_attributes: list[VariantAttributePairSchema]


class ProductVariantResponse(CamelModel):
    """Product variant detail response with nested SKUs."""

    id: uuid.UUID
    name_i18n: dict[str, str]
    description_i18n: dict[str, str] | None = None
    sort_order: int
    default_price: MoneySchema | None = None
    skus: list[SKUResponse]


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
    """Full product detail response with nested variants and attribute assignments."""

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
    created_at: datetime
    updated_at: datetime
    published_at: datetime | None = None
    min_price: int | None = None
    max_price: int | None = None
    price_currency: str | None = None
    variants: list[ProductVariantResponse]
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


ProductListResponse = PaginatedResponse[ProductListItemResponse]


# ---------------------------------------------------------------------------
# Product media schemas
# ---------------------------------------------------------------------------


class ProductMediaUploadRequest(CamelModel):
    """Request body for reserving a media upload slot."""

    variant_id: uuid.UUID | None = None
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

    variant_id: uuid.UUID | None = None
    media_type: str = Field(..., pattern=r"^(image|video|model_3d|document)$")
    role: str = Field(..., pattern=r"^(main|hover|gallery|hero_video|size_guide|packaging)$")
    external_url: str = Field(..., min_length=1, max_length=2048, pattern=r"^https?://")
    sort_order: int = Field(0, ge=0)


class ProductMediaResponse(CamelModel):
    """Media asset detail response."""

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


ProductMediaListResponse = PaginatedResponse[ProductMediaResponse]


class MediaConfirmResponse(CamelModel):
    """Response returned after confirming a media upload."""

    message: str = "Upload confirmed, processing started"


# ---------------------------------------------------------------------------
# ProductVariant request/response schemas
# ---------------------------------------------------------------------------


class ProductVariantCreateRequest(CamelModel):
    """Request body for creating a product variant."""

    name_i18n: I18nDict = Field(..., min_length=1)
    description_i18n: I18nDict | None = None
    sort_order: int = Field(0, ge=0)
    default_price_amount: int | None = Field(None, ge=0)
    default_price_currency: str | None = Field(
        None, min_length=3, max_length=3, pattern=r"^[A-Z]{3}$"
    )


class ProductVariantCreateResponse(CamelModel):
    """Response returned after successful variant creation."""

    id: uuid.UUID
    message: str


ProductVariantListResponse = PaginatedResponse[ProductVariantResponse]


class ProductVariantUpdateRequest(CamelModel):
    """Partial update request for a product variant (PATCH semantics)."""

    name_i18n: I18nDict | None = None
    description_i18n: I18nDict | None = None
    sort_order: int | None = Field(None, ge=0)
    default_price_amount: int | None = Field(None, ge=0)
    default_price_currency: str | None = Field(
        None, min_length=3, max_length=3, pattern=r"^[A-Z]{3}$"
    )

    @model_validator(mode="after")
    def at_least_one_field(self) -> ProductVariantUpdateRequest:
        """Ensure at least one field is provided for update."""
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        return self


class ProductVariantUpdateResponse(CamelModel):
    """Response returned after successful variant update."""

    id: uuid.UUID
    message: str


# ---------------------------------------------------------------------------
# SKU list response
# ---------------------------------------------------------------------------


SKUListResponse = PaginatedResponse[SKUResponse]


# ---------------------------------------------------------------------------
# ProductAttribute list response
# ---------------------------------------------------------------------------


ProductAttributeListResponse = PaginatedResponse[ProductAttributeResponse]


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
