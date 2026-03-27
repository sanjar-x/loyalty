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

from pydantic import AfterValidator, ConfigDict, Field, computed_field, model_validator

from src.shared.schemas import CamelModel

S = TypeVar("S")


class PaginatedResponse(CamelModel, Generic[S]):
    """Generic paginated list response with camelCase serialization."""

    items: list[S]
    total: int
    offset: int
    limit: int

    @computed_field
    @property
    def has_next(self) -> bool:
        """True when more items exist beyond the current page."""
        return self.offset + len(self.items) < self.total


# ---------------------------------------------------------------------------
# i18n language code validation
# ---------------------------------------------------------------------------

# ISO 639-1 two-letter language codes (lowercase).
_LANG_CODE_RE = re.compile(r"^[a-z]{2}$")


_MAX_I18N_ENTRIES = 20
_MAX_I18N_VALUE_LENGTH = 10_000


_REQUIRED_LOCALES = {"ru", "en"}


def _validate_i18n_keys(value: dict[str, str]) -> dict[str, str]:
    """Validate i18n dict: ISO 639-1 keys, required locales, bounded entries and value lengths."""
    if len(value) > _MAX_I18N_ENTRIES:
        raise ValueError(
            f"Too many language entries: {len(value)} (max {_MAX_I18N_ENTRIES})"
        )
    missing = _REQUIRED_LOCALES - value.keys()
    if missing:
        raise ValueError(
            f"Missing required locales: {', '.join(sorted(missing))}. "
            f"Both 'ru' and 'en' must be provided."
        )
    for key, val in value.items():
        if not _LANG_CODE_RE.match(key):
            raise ValueError(
                f"Invalid language code '{key}'. "
                f"Keys must be ISO 639-1 two-letter lowercase codes (e.g. 'en', 'ru')."
            )
        if len(val) > _MAX_I18N_VALUE_LENGTH:
            raise ValueError(
                f"Value for '{key}' too long: {len(val)} chars (max {_MAX_I18N_VALUE_LENGTH})"
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


class CategoryCreateRequest(CamelModel):
    """Request body for creating a new category."""

    name_i18n: I18nDict = Field(
        ..., min_length=1, examples=[{"ru": "Кроссовки", "en": "Sneakers"}]
    )
    slug: str = Field(
        ...,
        min_length=3,
        max_length=255,
        pattern=r"^[a-z0-9-]+$",
        examples=["sneakers"],
    )
    parent_id: uuid.UUID | None = Field(
        None, description="Parent category ID (optional)"
    )
    sort_order: int = Field(0, ge=0, description="Display ordering among siblings")
    template_id: uuid.UUID | None = Field(None, description="Attribute template UUID.")


class CategoryCreateResponse(CamelModel):
    """Response returned after successful category creation."""

    id: uuid.UUID
    message: str


class CategoryTreeResponse(CamelModel):
    """Recursive tree node for the category hierarchy response."""

    id: uuid.UUID
    name_i18n: dict[str, str]
    slug: str
    full_slug: str
    level: int
    sort_order: int
    children: list[CategoryTreeResponse]

    model_config = ConfigDict(from_attributes=True)


class CategoryResponse(CamelModel):
    """Single category detail response."""

    id: uuid.UUID
    name_i18n: dict[str, str]
    slug: str
    full_slug: str
    level: int
    sort_order: int
    parent_id: uuid.UUID | None = None


class CategoryUpdateRequest(CamelModel):
    """Partial update request -- all fields optional (PATCH semantics)."""

    name_i18n: I18nDict | None = Field(None, min_length=1)
    slug: str | None = Field(
        None, min_length=3, max_length=255, pattern=r"^[a-z0-9-]+$"
    )
    sort_order: int | None = Field(None, ge=0)
    template_id: uuid.UUID | None = Field(None, description="Attribute template UUID.")

    @model_validator(mode="after")
    def at_least_one_field(self) -> CategoryUpdateRequest:
        if not self.model_fields_set:
            raise ValueError(
                "At least one field (nameI18n, slug, sortOrder, or templateId) must be provided"
            )
        return self


CategoryListResponse = PaginatedResponse[CategoryResponse]


class BulkCategoryItem(CamelModel):
    """A single category within a bulk-create request."""

    name_i18n: I18nDict = Field(..., min_length=1)
    slug: str = Field(..., min_length=3, max_length=255, pattern=r"^[a-z0-9-]+$")
    parent_id: uuid.UUID | None = Field(
        None, description="Existing parent category UUID"
    )
    parent_ref: str | None = Field(
        None,
        max_length=100,
        description="Reference to another item's 'ref' in this batch (for nested trees)",
    )
    ref: str | None = Field(
        None,
        max_length=100,
        description="Key so other items can reference this one as parent",
    )
    sort_order: int = Field(0, ge=0)
    template_id: uuid.UUID | None = None


class BulkCreateCategoriesRequest(CamelModel):
    """Request body for bulk-creating categories (max 200)."""

    items: list[BulkCategoryItem] = Field(..., min_length=1, max_length=200)
    skip_existing: bool = Field(
        False,
        description="If true, silently skip categories with conflicting slug instead of failing.",
    )


class BulkCategoryCreatedItemResponse(CamelModel):
    """Info about a single created category in the bulk response."""

    id: uuid.UUID
    slug: str
    full_slug: str
    level: int
    ref: str | None = None


class BulkCreateCategoriesResponse(CamelModel):
    """Response from bulk category creation."""

    created_count: int
    skipped_count: int
    created: list[BulkCategoryCreatedItemResponse]
    skipped_slugs: list[str]


class BrandCreateRequest(CamelModel):
    """Request body for creating a new brand, with optional logo fields."""

    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=255, pattern=r"^[a-z0-9-]+$")
    logo_url: str | None = Field(None, max_length=2048, pattern=r"^https://")
    logo_storage_object_id: uuid.UUID | None = None


class BrandCreateResponse(CamelModel):
    """Response after brand creation."""

    id: uuid.UUID


class BrandResponse(CamelModel):
    """Brand detail response."""

    id: uuid.UUID
    name: str
    slug: str
    logo_url: str | None = None


class BrandUpdateRequest(CamelModel):
    """Partial update request -- all fields optional (PATCH semantics)."""

    name: str | None = Field(None, min_length=1, max_length=255)
    slug: str | None = Field(
        None, min_length=1, max_length=255, pattern=r"^[a-z0-9-]+$"
    )
    logo_url: str | None = Field(None, max_length=2048, pattern=r"^https://")
    logo_storage_object_id: uuid.UUID | None = None

    @model_validator(mode="after")
    def at_least_one_field(self) -> BrandUpdateRequest:
        if not self.model_fields_set:
            raise ValueError(
                "At least one field (name, slug, logoUrl, or logoStorageObjectId) "
                "must be provided"
            )
        return self


BrandListResponse = PaginatedResponse[BrandResponse]


class BulkBrandItem(CamelModel):
    """A single brand within a bulk-create request."""

    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=255, pattern=r"^[a-z0-9-]+$")
    logo_url: str | None = Field(None, max_length=2048, pattern=r"^https://")


class BulkCreateBrandsRequest(CamelModel):
    """Request body for bulk-creating brands (max 100)."""

    items: list[BulkBrandItem] = Field(..., min_length=1, max_length=100)
    skip_existing: bool = Field(
        False,
        description="If true, silently skip brands with existing slug/name instead of failing.",
    )


class BulkCreateBrandsResponse(CamelModel):
    """Response from bulk brand creation."""

    created_count: int
    skipped_count: int
    ids: list[uuid.UUID]
    skipped_slugs: list[str]


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
    name_i18n: I18nDict = Field(
        ..., min_length=1, examples=[{"en": "Color", "ru": "Цвет"}]
    )
    description_i18n: I18nDict = Field(default_factory=dict)
    data_type: Literal["string", "integer", "float", "boolean"] = Field(
        ..., examples=["string"]
    )
    ui_type: Literal[
        "text_button", "color_swatch", "dropdown", "checkbox", "range_slider"
    ] = Field(..., examples=["color_swatch"])
    is_dictionary: bool = True
    group_id: uuid.UUID | None = None
    level: Literal["product", "variant"] = Field(
        "product", examples=["product", "variant"]
    )
    is_filterable: bool = False
    is_searchable: bool = False
    search_weight: int = Field(5, ge=1, le=10)
    is_comparable: bool = False
    is_visible_on_card: bool = False
    validation_rules: BoundedJsonDict | None = None


class AttributeCreateResponse(CamelModel):
    """Response after attribute creation."""

    id: uuid.UUID


class AttributeResponse(CamelModel):
    """Full attribute detail response."""

    id: uuid.UUID
    code: str = Field(..., json_schema_extra={"readOnly": True})
    slug: str = Field(..., json_schema_extra={"readOnly": True})
    name_i18n: dict[str, str]
    description_i18n: dict[str, str]
    data_type: str = Field(..., json_schema_extra={"readOnly": True})
    ui_type: str
    is_dictionary: bool
    group_id: uuid.UUID | None
    level: str
    is_filterable: bool
    is_searchable: bool
    search_weight: int
    is_comparable: bool
    is_visible_on_card: bool
    validation_rules: dict[str, Any] | None = None


class AttributeUpdateRequest(CamelModel):
    """Partial update request -- code, slug, data_type are immutable."""

    name_i18n: I18nDict | None = Field(None, min_length=1)
    description_i18n: I18nDict | None = None
    ui_type: (
        Literal["text_button", "color_swatch", "dropdown", "checkbox", "range_slider"]
        | None
    ) = None
    group_id: uuid.UUID | None = None
    level: Literal["product", "variant"] | None = None
    is_filterable: bool | None = None
    is_searchable: bool | None = None
    search_weight: int | None = Field(None, ge=1, le=10)
    is_comparable: bool | None = None
    is_visible_on_card: bool | None = None
    validation_rules: BoundedJsonDict | None = None

    @model_validator(mode="after")
    def at_least_one_field(self) -> AttributeUpdateRequest:
        """Ensure at least one field is provided for update."""
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided for update")
        return self


AttributeListResponse = PaginatedResponse[AttributeResponse]


class BulkCreateAttributesRequest(CamelModel):
    """Request body for bulk-creating attributes (max 100)."""

    items: list[AttributeCreateRequest] = Field(..., min_length=1, max_length=100)
    skip_existing: bool = Field(
        False,
        description="If true, silently skip attributes with existing code/slug.",
    )


class BulkCreateAttributesResponse(CamelModel):
    """Response from bulk attribute creation."""

    created_count: int
    skipped_count: int
    ids: list[uuid.UUID]
    skipped_codes: list[str]


# ---------------------------------------------------------------------------
# AttributeValue schemas
# ---------------------------------------------------------------------------


class AttributeValueCreateRequest(CamelModel):
    """Request body for adding a value to an attribute."""

    code: str = Field(
        ..., min_length=1, max_length=100, pattern=r"^[a-z0-9_]+$", examples=["red"]
    )
    slug: str = Field(
        ..., min_length=1, max_length=255, pattern=r"^[a-z0-9-]+$", examples=["red"]
    )
    value_i18n: I18nDict = Field(
        ..., min_length=1, examples=[{"en": "Red", "ru": "Красный"}]
    )
    search_aliases: list[Annotated[str, Field(max_length=100)]] = Field(
        default_factory=list,
        max_length=50,
        examples=[["scarlet", "crimson"]],
        description="Search synonyms (max 50 entries, each max 100 chars)",
    )
    meta_data: BoundedJsonDict = Field(
        default_factory=dict, examples=[{"hex": "#FF0000"}]
    )
    value_group: str | None = Field(None, max_length=100, examples=["Warm tones"])
    sort_order: int = Field(0, ge=0, description="Display ordering among values")


class AttributeValueCreateResponse(CamelModel):
    """Response after attribute value creation."""

    id: uuid.UUID


class AttributeValueResponse(CamelModel):
    """Full attribute value detail response."""

    id: uuid.UUID
    attribute_id: uuid.UUID
    code: str = Field(..., json_schema_extra={"readOnly": True})
    slug: str = Field(..., json_schema_extra={"readOnly": True})
    value_i18n: dict[str, str]
    search_aliases: list[str]
    meta_data: dict[str, Any]
    value_group: str | None = None
    sort_order: int
    is_active: bool


class AttributeValueUpdateRequest(CamelModel):
    """Partial update request -- code and slug are immutable."""

    value_i18n: I18nDict | None = Field(None, min_length=1)
    search_aliases: list[Annotated[str, Field(max_length=100)]] | None = Field(
        None, max_length=50
    )
    meta_data: BoundedJsonDict | None = None
    value_group: str | None = Field(None, max_length=100)
    sort_order: int | None = Field(None, ge=0)

    @model_validator(mode="after")
    def at_least_one_field(self) -> AttributeValueUpdateRequest:
        """Ensure at least one field is provided for update."""
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided for update")
        return self


AttributeValueListResponse = PaginatedResponse[AttributeValueResponse]


class AttributeValueActiveResponse(CamelModel):
    """Response after activating or deactivating an attribute value."""

    id: uuid.UUID
    is_active: bool


class BulkAttributeValueItem(CamelModel):
    """A single value item within a bulk-add request."""

    code: str = Field(
        ..., min_length=1, max_length=100, pattern=r"^[a-z0-9_-]+$", examples=["red"]
    )
    slug: str = Field(
        ..., min_length=1, max_length=255, pattern=r"^[a-z0-9-]+$", examples=["red"]
    )
    value_i18n: I18nDict = Field(
        ..., min_length=1, examples=[{"en": "Red", "ru": "Красный"}]
    )
    search_aliases: list[Annotated[str, Field(max_length=100)]] | None = Field(
        None,
        max_length=50,
        description="Search synonyms (max 50 entries, each max 100 chars)",
    )
    meta_data: BoundedJsonDict | None = None
    value_group: str | None = Field(None, max_length=100)
    sort_order: int = Field(0, ge=0)


class BulkAddAttributeValuesRequest(CamelModel):
    """Request body for bulk-adding values to an attribute."""

    items: list[BulkAttributeValueItem] = Field(..., min_length=1, max_length=100)


class BulkAddAttributeValuesResponse(CamelModel):
    """Response from bulk attribute value creation."""

    created_count: int
    ids: list[uuid.UUID]


class ReorderItemRequest(CamelModel):
    """A single reorder instruction."""

    value_id: uuid.UUID
    sort_order: int = Field(..., ge=0)


class ReorderAttributeValuesRequest(CamelModel):
    """Request body for bulk-reordering attribute values."""

    items: list[ReorderItemRequest] = Field(..., min_length=1, max_length=500)


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
    name: str | None = Field(
        None, description="Projected name from nameI18n when ?lang is specified"
    )
    data_type: str
    ui_type: str
    is_dictionary: bool
    selection_mode: str
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
    name: str | None = Field(
        None, description="Projected name from nameI18n when ?lang is specified"
    )
    data_type: str
    ui_type: str
    level: str
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
    name: str | None = Field(
        None, description="Projected name from nameI18n when ?lang is specified"
    )
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
    name: str | None = Field(
        None, description="Projected name from nameI18n when ?lang is specified"
    )
    description_i18n: dict[str, str]
    data_type: str
    ui_type: str
    is_dictionary: bool
    level: str
    requirement_level: str
    is_filterable: bool
    is_visible_on_card: bool
    is_comparable: bool
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
    source_url: str | None = Field(None, max_length=1024, pattern=r"^https?://")
    tags: list[Annotated[str, Field(max_length=200)]] = Field(
        default_factory=list, max_length=50
    )


class ProductCreateResponse(CamelModel):
    """Response returned after successful product creation."""

    id: uuid.UUID
    default_variant_id: uuid.UUID
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
    country_of_origin: str | None = Field(
        None, min_length=2, max_length=2, pattern=r"^[A-Z]{2}$"
    )
    tags: list[Annotated[str, Field(max_length=200)]] | None = Field(
        None, max_length=50
    )
    version: int | None = None

    @model_validator(mode="after")
    def at_least_one_field(self) -> ProductUpdateRequest:
        """Ensure at least one non-version field is provided."""
        if not (self.model_fields_set - {"version"}):
            raise ValueError("At least one field besides 'version' must be provided")
        return self


class ProductStatusChangeRequest(CamelModel):
    """Request body for changing a product's status."""

    status: Literal[
        "draft", "enriching", "ready_for_review", "published", "archived"
    ] = Field(...)


class SKUCreateRequest(CamelModel):
    """Request body for adding a SKU (variant) to a product."""

    sku_code: str = Field(..., min_length=1, max_length=100)
    price_amount: int | None = Field(None, ge=0)
    price_currency: str = Field(
        "RUB", min_length=3, max_length=3, pattern=r"^[A-Z]{3}$"
    )
    compare_at_price_amount: int | None = Field(None, ge=0)
    is_active: bool = True
    variant_attributes: list[VariantAttributePairSchema] = Field(
        default_factory=list, max_length=50
    )


class SKUCreateResponse(CamelModel):
    """Response returned after successful SKU creation."""

    id: uuid.UUID
    message: str


class SKUUpdateRequest(CamelModel):
    """Partial update request for a SKU -- all fields optional (PATCH semantics)."""

    sku_code: str | None = Field(None, min_length=1, max_length=100)
    price_amount: int | None = Field(None, ge=0)
    price_currency: str | None = Field(
        None, min_length=3, max_length=3, pattern=r"^[A-Z]{3}$"
    )
    compare_at_price_amount: int | None = None
    is_active: bool | None = None
    variant_attributes: list[VariantAttributePairSchema] | None = Field(
        None, max_length=50
    )
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


class BulkAssignProductAttributesRequest(CamelModel):
    """Request body for bulk product attribute assignment."""

    items: list[ProductAttributeAssignRequest] = Field(..., min_length=1, max_length=50)


class BulkAssignProductAttributesResponse(CamelModel):
    """Response from bulk attribute assignment."""

    assigned_count: int
    pav_ids: list[uuid.UUID]
    message: str


class ProductAttributeResponse(CamelModel):
    """Single product-attribute assignment detail response."""

    id: uuid.UUID
    product_id: uuid.UUID
    attribute_id: uuid.UUID
    attribute_value_id: uuid.UUID
    attribute_code: str = ""
    attribute_name_i18n: dict[str, str] = Field(default_factory=dict)
    attribute_value_code: str = ""
    attribute_value_name_i18n: dict[str, str] = Field(default_factory=dict)


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
    source_url: str | None = None
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


class AttributeSelectionSchema(CamelModel):
    """One attribute with multiple selected values for SKU matrix generation."""

    attribute_id: uuid.UUID
    value_ids: list[uuid.UUID] = Field(..., min_length=1, max_length=50)


class SKUMatrixGenerateRequest(CamelModel):
    """Request to generate SKU combinations from attribute selections."""

    attribute_selections: list[AttributeSelectionSchema] = Field(
        ..., min_length=1, max_length=10
    )
    price_amount: int | None = Field(None, ge=0)
    price_currency: str = Field(
        "RUB", min_length=3, max_length=3, pattern=r"^[A-Z]{3}$"
    )
    compare_at_price_amount: int | None = Field(None, ge=0)
    is_active: bool = True


class SKUMatrixGenerateResponse(CamelModel):
    """Response from SKU matrix generation."""

    created_count: int
    skipped_count: int
    sku_ids: list[uuid.UUID]
    message: str


# ---------------------------------------------------------------------------
# ProductAttribute list response
# ---------------------------------------------------------------------------


ProductAttributeListResponse = PaginatedResponse[ProductAttributeResponse]


# ---------------------------------------------------------------------------
# MediaAsset schemas
# ---------------------------------------------------------------------------


class MediaAssetCreateRequest(CamelModel):
    """Request body for adding a media asset to a product."""

    storage_object_id: uuid.UUID | None = None
    variant_id: uuid.UUID | None = None
    media_type: Literal["image", "video", "model_3d", "document"] = "image"
    role: Literal[
        "main", "hover", "gallery", "hero_video", "size_guide", "packaging"
    ] = "gallery"
    sort_order: int = Field(0, ge=0)
    is_external: bool = False
    url: str | None = Field(None, max_length=1024, pattern=r"^https?://")

    @model_validator(mode="after")
    def validate_media_source(self) -> MediaAssetCreateRequest:
        """External assets must have a URL; internal assets must have a storageObjectId."""
        if self.is_external and not self.url:
            raise ValueError("External media assets must have a URL")
        if not self.is_external and not self.storage_object_id:
            raise ValueError("Internal media assets must have a storageObjectId")
        return self


class MediaAssetCreateResponse(CamelModel):
    """Response returned after successful media asset creation."""

    id: uuid.UUID
    message: str


class MediaAssetUpdateResponse(CamelModel):
    """Response returned after successful media asset update."""

    id: uuid.UUID
    message: str


class MediaAssetUpdateRequest(CamelModel):
    """Partial update request for a media asset (PATCH semantics)."""

    variant_id: uuid.UUID | None = None
    role: Literal[
        "main", "hover", "gallery", "hero_video", "size_guide", "packaging"
    ] | None = None
    sort_order: int | None = Field(None, ge=0)

    @model_validator(mode="after")
    def at_least_one_field(self) -> MediaAssetUpdateRequest:
        """Ensure at least one field is provided for update."""
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        return self


class MediaAssetResponse(CamelModel):
    """Full media asset detail response."""

    id: uuid.UUID
    product_id: uuid.UUID
    variant_id: uuid.UUID | None = None
    media_type: str
    role: str
    sort_order: int
    storage_object_id: uuid.UUID | None = None
    url: str | None = None
    is_external: bool
    image_variants: list[dict[str, Any]] | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


MediaAssetListResponse = PaginatedResponse[MediaAssetResponse]


class ReorderMediaItemSchema(CamelModel):
    """A single media asset reorder instruction."""

    media_id: uuid.UUID
    sort_order: int = Field(..., ge=0)


class MediaAssetReorderRequest(CamelModel):
    """Request body for bulk-reordering media assets."""

    items: list[ReorderMediaItemSchema] = Field(..., min_length=1, max_length=100)


# ---------------------------------------------------------------------------
# AttributeTemplate schemas
# ---------------------------------------------------------------------------


class CloneAttributeTemplateRequest(CamelModel):
    """Request body for cloning an existing attribute template."""

    source_template_id: uuid.UUID
    new_code: str = Field(
        ...,
        min_length=1,
        max_length=100,
        pattern=r"^[a-z0-9_-]+$",
        description="Unique machine-readable code for the clone.",
    )
    new_name_i18n: I18nDict = Field(..., min_length=1)
    new_description_i18n: I18nDict | None = None


class CloneAttributeTemplateResponse(CamelModel):
    """Response after template cloning."""

    id: uuid.UUID
    bindings_copied: int
    message: str = "Template cloned successfully"


class AttributeTemplateCreateRequest(CamelModel):
    """Request body for creating a new attribute template."""

    code: str = Field(
        ...,
        min_length=1,
        max_length=100,
        pattern=r"^[a-z0-9_]+$",
        description="Unique machine-readable code.",
    )
    name_i18n: I18nDict = Field(..., min_length=1)
    description_i18n: I18nDict | None = Field(default_factory=dict)
    sort_order: int = Field(0, ge=0)


class AttributeTemplateCreateResponse(CamelModel):
    """Response for template creation."""

    id: uuid.UUID
    message: str = "Attribute template created"


class AttributeTemplateResponse(CamelModel):
    """Full attribute template representation."""

    id: uuid.UUID
    code: str = Field(..., json_schema_extra={"readOnly": True})
    name_i18n: dict[str, str]
    description_i18n: dict[str, str]
    sort_order: int


class AttributeTemplateUpdateRequest(CamelModel):
    """Request body for updating an attribute template (PATCH semantics)."""

    name_i18n: I18nDict | None = None
    description_i18n: I18nDict | None = None
    sort_order: int | None = Field(None, ge=0)

    @model_validator(mode="after")
    def at_least_one_field(self) -> AttributeTemplateUpdateRequest:
        if not self.model_fields_set:
            raise ValueError(
                "At least one of nameI18n, descriptionI18n, or sortOrder must be provided"
            )
        return self


AttributeTemplateListResponse = PaginatedResponse[AttributeTemplateResponse]


# ---------------------------------------------------------------------------
# TemplateAttributeBinding schemas
# ---------------------------------------------------------------------------


class TemplateAttributeBindingRequest(CamelModel):
    """Request body for binding an attribute to a template."""

    attribute_id: uuid.UUID
    sort_order: int = Field(0, ge=0)
    requirement_level: str = Field(
        "optional", pattern=r"^(required|recommended|optional)$"
    )
    filter_settings: BoundedJsonDict | None = Field(
        None,
        description="Opaque frontend config for filter UI (max 10 KB). Not interpreted by backend.",
    )


class TemplateAttributeBindingResponse(CamelModel):
    """Response for binding creation."""

    id: uuid.UUID
    message: str = "Attribute bound to template"


class TemplateAttributeBindingDetailResponse(CamelModel):
    """Detailed binding info with joined attribute metadata."""

    id: uuid.UUID
    template_id: uuid.UUID
    attribute_id: uuid.UUID
    sort_order: int
    requirement_level: str
    filter_settings: dict[str, Any] | None = None
    attribute_code: str = ""
    attribute_name_i18n: dict[str, str] = {}
    attribute_data_type: str = ""
    attribute_ui_type: str = ""
    attribute_level: str = ""
    attribute_is_filterable: bool = False


TemplateAttributeBindingListResponse = PaginatedResponse[
    TemplateAttributeBindingDetailResponse
]


class TemplateAttributeBindingUpdateRequest(CamelModel):
    """PATCH request for updating a binding."""

    sort_order: int | None = Field(None, ge=0)
    requirement_level: str | None = Field(
        None, pattern=r"^(required|recommended|optional)$"
    )
    filter_settings: BoundedJsonDict | None = Field(
        None,
        description="Opaque frontend config for filter UI (max 10 KB). Not interpreted by backend.",
    )


class BindingReorderItemSchema(CamelModel):
    """A single reorder item."""

    binding_id: uuid.UUID
    sort_order: int = Field(..., ge=0)


class TemplateBindingReorderRequest(CamelModel):
    """Request for reordering bindings."""

    items: list[BindingReorderItemSchema] = Field(..., min_length=1, max_length=500)


# ---------------------------------------------------------------------------
# Attribute usage analytics
# ---------------------------------------------------------------------------


class AttributeUsageTemplateItem(CamelModel):
    """A template that binds a given attribute."""

    id: uuid.UUID
    code: str
    name_i18n: dict[str, str]


class AttributeUsageCategoryItem(CamelModel):
    """A category that inherits a given attribute."""

    id: uuid.UUID
    full_slug: str
    name_i18n: dict[str, str]


class AttributeUsageResponse(CamelModel):
    """Analytics response showing where an attribute is used."""

    template_count: int
    templates: list[AttributeUsageTemplateItem]
    category_count: int
    categories: list[AttributeUsageCategoryItem]
    product_count: int


# ---------------------------------------------------------------------------
# Product completeness check
# ---------------------------------------------------------------------------


class MissingAttributeItem(CamelModel):
    """An attribute that is missing from a product."""

    attribute_id: uuid.UUID
    code: str
    name_i18n: dict[str, str]


class ProductCompletenessResponse(CamelModel):
    """Response showing product attribute completeness against template."""

    is_complete: bool
    total_required: int
    filled_required: int
    total_recommended: int
    filled_recommended: int
    missing_required: list[MissingAttributeItem]
    missing_recommended: list[MissingAttributeItem]


# ---------------------------------------------------------------------------
# Enriched binding response (with affected categories count)
# ---------------------------------------------------------------------------


class TemplateAttributeBindingEnrichedResponse(CamelModel):
    """Response for binding creation, enriched with affected categories count."""

    id: uuid.UUID
    affected_categories_count: int
    message: str = "Attribute bound to template"
