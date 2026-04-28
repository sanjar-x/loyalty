"""Pydantic schemas for pricing HTTP endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from src.modules.pricing.domain.value_objects import (
    ProfileStatus,
    RoundingMode,
    VariableDataType,
    VariableScope,
)
from src.shared.schemas import CamelModel


class UpsertProductPricingProfileRequest(CamelModel):
    """Body of ``PUT /pricing/products/{product_id}/profile``."""

    model_config = ConfigDict(extra="forbid")

    values: dict[str, Decimal] = Field(
        default_factory=dict,
        description="Map of variable_code -> decimal value (e.g. {'purchase_price_cny': '199.50'}).",
    )
    context_id: uuid.UUID | None = Field(
        default=None,
        description="Resolved pricing context ID (optional in this slice).",
    )
    context_id_provided: bool = Field(
        default=False,
        description=(
            "Set to true if the caller is intentionally writing `context_id` "
            "(including null to clear it). False = leave existing value untouched."
        ),
    )
    status: ProfileStatus = Field(
        default=ProfileStatus.DRAFT,
        description="Desired profile status.",
    )
    expected_version_lock: int | None = Field(
        default=None,
        ge=0,
        description=(
            "Expected current `version_lock` for optimistic locking; required "
            "when updating an existing profile. Omit on create."
        ),
    )


class UpsertProductPricingProfileResponse(CamelModel):
    """Response body for upsert."""

    model_config = ConfigDict(extra="forbid")

    profile_id: uuid.UUID
    product_id: uuid.UUID
    version_lock: int
    status: str
    created: bool


class ProductPricingProfileResponse(CamelModel):
    """Response body for GET."""

    model_config = ConfigDict(extra="forbid")

    profile_id: uuid.UUID
    product_id: uuid.UUID
    context_id: uuid.UUID | None
    values: dict[str, Decimal]
    status: str
    version_lock: int
    created_at: datetime
    updated_at: datetime
    updated_by: uuid.UUID | None


# ---------------------------------------------------------------------------
# Variable registry schemas
# ---------------------------------------------------------------------------


class I18nText(BaseModel):
    """i18n labels with mandatory ``ru`` and ``en`` fields.

    Modelled as a free dict to allow additional language tags without breaking
    clients; the domain layer enforces presence of required keys.
    """

    model_config = ConfigDict(extra="allow")

    ru: str
    en: str


class CreateVariableRequest(CamelModel):
    """Body of ``POST /pricing/variables``."""

    model_config = ConfigDict(extra="forbid")

    code: str = Field(
        ...,
        min_length=2,
        max_length=64,
        pattern=r"^[a-z][a-z0-9_]{1,63}$",
        description="Unique snake_case code.",
    )
    scope: VariableScope = Field(..., description="Immutable after create.")
    data_type: VariableDataType = Field(..., description="Immutable after create.")
    unit: str = Field(
        ...,
        min_length=1,
        max_length=32,
        description="Unit code (immutable). E.g. RUB, RUB/CNY, %.",
    )
    name: I18nText
    description: I18nText | None = None
    is_required: bool = False
    default_value: Decimal | None = None
    is_system: bool = False
    is_fx_rate: bool = False
    max_age_days: int | None = Field(default=None, ge=1, le=365)


class UpdateVariableRequest(CamelModel):
    """Body of ``PATCH /pricing/variables/{id}``.

    Only ``name``, ``description``, ``is_required``, ``default_value``, and
    ``max_age_days`` are mutable. Immutable fields may be supplied for
    front-end safety and will be validated against the persisted row; a
    mismatch returns 422.
    """

    model_config = ConfigDict(extra="forbid")

    expected_version_lock: int | None = Field(default=None, ge=0)
    name: I18nText | None = None
    description: I18nText | None = None
    is_required: bool | None = None
    default_value: Decimal | None = None
    default_value_provided: bool = False
    max_age_days: int | None = None
    max_age_days_provided: bool = False
    # Immutable guard rails — server rejects if these differ from persisted row.
    code: str | None = None
    scope: VariableScope | None = None
    data_type: VariableDataType | None = None
    unit: str | None = None
    is_fx_rate: bool | None = None


class VariableResponse(CamelModel):
    """Response body for variable reads and writes."""

    model_config = ConfigDict(extra="forbid")

    variable_id: uuid.UUID
    code: str
    scope: str
    data_type: str
    unit: str
    name: dict[str, str]
    description: dict[str, str]
    is_required: bool
    default_value: Decimal | None
    is_system: bool
    is_fx_rate: bool
    is_user_editable_at_runtime: bool
    max_age_days: int | None
    version_lock: int
    created_at: datetime
    updated_at: datetime
    updated_by: uuid.UUID | None


class VariableListResponse(CamelModel):
    model_config = ConfigDict(extra="forbid")

    items: list[VariableResponse]
    total: int


class CreateVariableResponse(CamelModel):
    model_config = ConfigDict(extra="forbid")

    variable_id: uuid.UUID
    code: str
    version_lock: int


# ---------------------------------------------------------------------------
# Pricing contexts
# ---------------------------------------------------------------------------


class CreateContextRequest(CamelModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(..., min_length=2, max_length=64)
    name: I18nText
    rounding_mode: RoundingMode = RoundingMode.HALF_UP
    rounding_step: Decimal = Field(default=Decimal("0.01"), gt=Decimal("0"))
    margin_floor_pct: Decimal = Field(
        default=Decimal("0"), ge=Decimal("0"), le=Decimal("1")
    )
    evaluation_timeout_ms: int = Field(default=50, ge=1, le=60_000)
    simulation_threshold: int = Field(default=0, ge=0)
    approval_required_on_publish: bool = False
    range_base_variable_code: str | None = Field(
        default=None, min_length=2, max_length=64
    )


class UpdateContextRequest(CamelModel):
    """PATCH body for a pricing context. All fields optional.

    ``code`` is rejected at the handler level (immutable); the schema still
    accepts it so the handler can return a specific 422 error.
    """

    model_config = ConfigDict(extra="forbid")

    expected_version_lock: int | None = Field(default=None, ge=0)
    code: str | None = None
    name: I18nText | None = None
    rounding_mode: RoundingMode | None = None
    rounding_step: Decimal | None = Field(default=None, gt=Decimal("0"))
    margin_floor_pct: Decimal | None = Field(
        default=None, ge=Decimal("0"), le=Decimal("1")
    )
    evaluation_timeout_ms: int | None = Field(default=None, ge=1, le=60_000)
    simulation_threshold: int | None = Field(default=None, ge=0)
    approval_required_on_publish: bool | None = None
    range_base_variable_code: str | None = Field(
        default=None, min_length=2, max_length=64
    )
    range_base_variable_code_provided: bool = False


class FreezeContextRequest(CamelModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(..., min_length=1, max_length=1024)


class PricingContextResponse(CamelModel):
    context_id: uuid.UUID
    code: str
    name: dict[str, str]
    is_active: bool
    is_frozen: bool
    freeze_reason: str | None
    rounding_mode: str
    rounding_step: Decimal
    margin_floor_pct: Decimal
    evaluation_timeout_ms: int
    simulation_threshold: int
    approval_required_on_publish: bool
    range_base_variable_code: str | None
    active_formula_version_id: uuid.UUID | None
    version_lock: int
    created_at: datetime
    updated_at: datetime
    updated_by: uuid.UUID | None


class ContextListResponse(CamelModel):
    items: list[PricingContextResponse]
    total: int


class CreateContextResponse(CamelModel):
    context_id: uuid.UUID
    code: str
    version_lock: int


class MutateContextResponse(CamelModel):
    context_id: uuid.UUID
    version_lock: int


# ---------------------------------------------------------------------------
# Formula version schemas (Slice 4)
# ---------------------------------------------------------------------------


class UpsertFormulaDraftRequest(CamelModel):
    """Body of ``PUT /pricing/contexts/{context_id}/formula/draft``."""

    model_config = ConfigDict(extra="forbid")

    ast: dict = Field(
        description=(
            "Formula AST (shape: {version: int, bindings: [{name, component_tag, expr}, ...]}). "
            "Last binding must have name='final_price' and component_tag='final_price'."
        )
    )
    expected_version_lock: int | None = Field(
        default=None,
        description="Optimistic-lock value of the existing draft (if any).",
    )


class UpsertFormulaDraftResponse(CamelModel):
    version_id: uuid.UUID
    version_number: int
    version_lock: int
    created: bool


class FormulaVersionResponse(CamelModel):
    version_id: uuid.UUID
    context_id: uuid.UUID
    version_number: int
    status: str
    ast: dict
    published_at: datetime | None
    published_by: uuid.UUID | None
    version_lock: int
    created_at: datetime
    updated_at: datetime
    updated_by: uuid.UUID | None


class FormulaVersionListResponse(CamelModel):
    items: list[FormulaVersionResponse]
    total: int


class PublishFormulaResponse(CamelModel):
    version_id: uuid.UUID
    version_number: int
    previous_version_id: uuid.UUID | None


class RollbackFormulaResponse(CamelModel):
    version_id: uuid.UUID
    rolled_back_from_version_id: uuid.UUID | None


class DiscardFormulaDraftResponse(CamelModel):
    version_id: uuid.UUID


# ---------------------------------------------------------------------------
# Category pricing settings
# ---------------------------------------------------------------------------


class RangeBucketSchema(CamelModel):
    """Single range bucket ``[min, max)`` with per-range variable overrides."""

    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        description="Stable UUID of the bucket (frontend may omit to get a new one).",
    )
    min: Decimal = Field(..., description="Inclusive lower bound (>= 0).")
    max: Decimal | None = Field(
        default=None,
        description="Exclusive upper bound. ``null`` is allowed only on the last bucket.",
    )
    values: dict[str, Decimal] = Field(
        default_factory=dict,
        description="Per-range variable overrides, snake_case codes.",
    )


class UpsertCategoryPricingSettingsRequest(CamelModel):
    """Body of ``PUT /pricing/categories/{category_id}/pricing/{context_id}``."""

    model_config = ConfigDict(extra="forbid")

    values: dict[str, Decimal] = Field(
        default_factory=dict,
        description="Category-level variable values (e.g. default margin_pct).",
    )
    ranges: list[RangeBucketSchema] = Field(
        default_factory=list,
        description=(
            "Ordered list of non-overlapping contiguous buckets. "
            "When ``explicit_no_ranges=true`` this MUST be empty."
        ),
    )
    explicit_no_ranges: bool = Field(
        default=False,
        description=(
            "Set to ``true`` to explicitly declare that this category has no "
            "range buckets (disables any inherited ranges). Mutually exclusive "
            "with a non-empty ``ranges``."
        ),
    )
    expected_version_lock: int | None = Field(
        default=None,
        description="Optional optimistic-locking guard; rejected with 409 if mismatched.",
    )


class CategoryPricingSettingsResponse(CamelModel):
    """Response body for category pricing settings."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    category_id: uuid.UUID
    context_id: uuid.UUID
    values: dict[str, Decimal]
    ranges: list[RangeBucketSchema]
    explicit_no_ranges: bool
    version_lock: int
    created_at: datetime
    updated_at: datetime
    updated_by: uuid.UUID | None


class UpsertCategoryPricingSettingsResponse(CamelModel):
    settings_id: uuid.UUID
    category_id: uuid.UUID
    context_id: uuid.UUID
    version_lock: int
    created: bool


# ---------------------------------------------------------------------------
# SupplierType → PricingContext mapping
# ---------------------------------------------------------------------------


class UpsertSupplierTypeContextMappingRequest(CamelModel):
    """PUT body for ``/pricing/supplier-type-mapping/{supplier_type}``."""

    context_id: uuid.UUID = Field(..., description="Target pricing context id.")


class SupplierTypeContextMappingResponse(CamelModel):
    """Response body for a single supplier-type → context mapping."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    supplier_type: str
    context_id: uuid.UUID
    version_lock: int
    created_at: datetime
    updated_at: datetime
    updated_by: uuid.UUID | None


class SupplierTypeContextMappingListResponse(CamelModel):
    items: list[SupplierTypeContextMappingResponse]


class UpsertSupplierTypeContextMappingResponse(CamelModel):
    mapping_id: uuid.UUID
    supplier_type: str
    context_id: uuid.UUID
    version_lock: int
    created: bool


# ---------------------------------------------------------------------------
# Price preview
# ---------------------------------------------------------------------------


class PreviewPriceRequest(CamelModel):
    """Request body for ``POST /pricing/preview``."""

    product_id: uuid.UUID = Field(
        ...,
        description="Product whose pricing profile supplies scope=product_input values.",
    )
    category_id: uuid.UUID = Field(
        ...,
        description=(
            "Category whose pricing settings supply scope=category values. "
            "Caller must provide this (no cross-module lookup in v1)."
        ),
    )
    context_id: uuid.UUID = Field(
        ..., description="Pricing context. Selects the published formula to use."
    )
    supplier_id: uuid.UUID | None = Field(
        default=None,
        description=(
            "Optional supplier whose pricing settings supply scope=supplier "
            "values. When absent, supplier-scope variables fall back to "
            "their default values."
        ),
    )


class PreviewPriceResponse(CamelModel):
    """Response body for ``POST /pricing/preview``."""

    final_price: Decimal = Field(..., description="Computed final price (Decimal).")
    components: dict[str, Decimal] = Field(
        ...,
        description=(
            "Intermediate binding values, keyed by binding name. Includes "
            "``final_price`` as the last entry."
        ),
    )
    formula_version_id: uuid.UUID
    formula_version_number: int
    context_id: uuid.UUID


# ---------------------------------------------------------------------------
# Supplier pricing settings
# ---------------------------------------------------------------------------


class UpsertSupplierPricingSettingsRequest(CamelModel):
    """Body of ``PUT /pricing/suppliers/{supplier_id}/pricing``."""

    model_config = ConfigDict(extra="forbid")

    values: dict[str, Decimal] = Field(
        default_factory=dict,
        description="Supplier-level variable values (e.g. supplier margin).",
    )
    expected_version_lock: int | None = Field(
        default=None,
        description="Optional optimistic-locking guard; rejected with 409 if mismatched.",
    )


class SupplierPricingSettingsResponse(CamelModel):
    """Response body for supplier pricing settings."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    supplier_id: uuid.UUID
    values: dict[str, Decimal]
    version_lock: int
    created_at: datetime
    updated_at: datetime
    updated_by: uuid.UUID | None


class UpsertSupplierPricingSettingsResponse(CamelModel):
    settings_id: uuid.UUID
    supplier_id: uuid.UUID
    version_lock: int
    created: bool


# ---------------------------------------------------------------------------
# Context global variable values
# ---------------------------------------------------------------------------


class ContextGlobalValueItemResponse(CamelModel):
    """Single entry in the context global-values list."""

    model_config = ConfigDict(from_attributes=True)

    variable_code: str
    value: Decimal
    variable_name: dict[str, str] = Field(default_factory=dict)
    is_required: bool = False


class ContextGlobalValuesResponse(CamelModel):
    """Response body for ``GET /pricing/contexts/{id}/variables/values``."""

    model_config = ConfigDict(from_attributes=True)

    context_id: uuid.UUID
    values: list[ContextGlobalValueItemResponse]
    version_lock: int


class SetContextGlobalValueRequest(CamelModel):
    """Body of ``PUT /pricing/contexts/{id}/variables/values/{code}``."""

    model_config = ConfigDict(extra="forbid")

    value: Decimal = Field(
        description="New value for the global-scope variable on this context.",
    )
    version_lock: int = Field(
        ge=0,
        description="Current ``version_lock`` of the context (optimistic locking).",
    )


class SetContextGlobalValueResponse(CamelModel):
    """Response body after setting a global variable value."""

    model_config = ConfigDict(from_attributes=True)

    context_id: uuid.UUID
    variable_code: str
    value: Decimal
    version_lock: int


# ---------------------------------------------------------------------------
# Product profile required variables
# ---------------------------------------------------------------------------


class RequiredVariableItem(CamelModel):
    """A single product_input variable that needs to be filled."""

    model_config = ConfigDict(from_attributes=True)

    variable_id: uuid.UUID
    code: str
    name: dict[str, str]
    description: dict[str, str] = Field(default_factory=dict)
    data_type: VariableDataType
    unit: str | None = None
    default_value: Decimal | None = None
    is_system: bool = False


class RequiredVariablesResponse(CamelModel):
    """Response body for ``GET /pricing/products/{id}/profile/required-variables``."""

    model_config = ConfigDict(from_attributes=True)

    product_id: uuid.UUID
    variables: list[RequiredVariableItem]
