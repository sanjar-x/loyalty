"""Pricing domain events.

Events are emitted by pricing aggregates during business operations,
serialized via ``dataclasses.asdict()`` and persisted atomically to
the Outbox table. ``Decimal`` payload fields are serialized as strings
to survive JSON round-trips without precision loss; consumers parse
them back to ``Decimal`` as needed.

Validation and ``aggregate_id`` auto-fill come from
:class:`src.shared.interfaces.entities.ModuleDomainEvent`.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from src.shared.interfaces.entities import ModuleDomainEvent


@dataclass
class PricingEvent(ModuleDomainEvent, abstract=True):
    """Intermediate base for all pricing domain events."""

    aggregate_type: str = "pricing_profile"


@dataclass
class ProductPricingProfileCreatedEvent(
    PricingEvent,
    required_fields=("profile_id", "product_id"),
    aggregate_id_field="profile_id",
):
    """Emitted when a new ``ProductPricingProfile`` is created."""

    profile_id: uuid.UUID | None = None
    product_id: uuid.UUID | None = None
    context_id: uuid.UUID | None = None
    status: str = "draft"
    values: dict[str, str] = field(default_factory=dict)
    updated_by: uuid.UUID | None = None
    event_type: str = "ProductPricingProfileCreatedEvent"


@dataclass
class ProductPricingProfileUpdatedEvent(
    PricingEvent,
    required_fields=("profile_id", "product_id"),
    aggregate_id_field="profile_id",
):
    """Emitted when profile values, context, or status change.

    ``values`` is the full new value map (Decimal → str) — consumers wanting a
    diff can compute it against their own last-known state.
    """

    profile_id: uuid.UUID | None = None
    product_id: uuid.UUID | None = None
    context_id: uuid.UUID | None = None
    status: str = "draft"
    values: dict[str, str] = field(default_factory=dict)
    updated_by: uuid.UUID | None = None
    event_type: str = "ProductPricingProfileUpdatedEvent"


@dataclass
class ProductPricingProfileDeletedEvent(
    PricingEvent,
    required_fields=("profile_id", "product_id"),
    aggregate_id_field="profile_id",
):
    """Emitted when a profile is deleted (soft or hard)."""

    profile_id: uuid.UUID | None = None
    product_id: uuid.UUID | None = None
    event_type: str = "ProductPricingProfileDeletedEvent"


# ---------------------------------------------------------------------------
# Variable registry events
# ---------------------------------------------------------------------------


@dataclass
class VariableEvent(ModuleDomainEvent, abstract=True):
    """Intermediate base for all ``Variable``-registry domain events."""

    aggregate_type: str = "pricing_variable"


@dataclass
class VariableCreatedEvent(
    VariableEvent,
    required_fields=("variable_id", "code", "scope", "data_type", "unit"),
    aggregate_id_field="variable_id",
):
    """Emitted when a new ``Variable`` is registered."""

    variable_id: uuid.UUID | None = None
    code: str | None = None
    scope: str | None = None
    data_type: str | None = None
    unit: str | None = None
    is_fx_rate: bool = False
    is_system: bool = False
    is_required: bool = False
    default_value: str | None = None
    max_age_days: int | None = None
    updated_by: uuid.UUID | None = None
    event_type: str = "VariableCreatedEvent"


@dataclass
class VariableUpdatedEvent(
    VariableEvent,
    required_fields=("variable_id", "code"),
    aggregate_id_field="variable_id",
):
    """Emitted when mutable fields of a ``Variable`` change."""

    variable_id: uuid.UUID | None = None
    code: str | None = None
    is_required: bool = False
    default_value: str | None = None
    max_age_days: int | None = None
    name: dict[str, str] = field(default_factory=dict)
    description: dict[str, str] = field(default_factory=dict)
    updated_by: uuid.UUID | None = None
    event_type: str = "VariableUpdatedEvent"


@dataclass
class VariableDeletedEvent(
    VariableEvent,
    required_fields=("variable_id", "code"),
    aggregate_id_field="variable_id",
):
    """Emitted when a ``Variable`` is deleted."""

    variable_id: uuid.UUID | None = None
    code: str | None = None
    updated_by: uuid.UUID | None = None
    event_type: str = "VariableDeletedEvent"


# ---------------------------------------------------------------------------
# Pricing context events
# ---------------------------------------------------------------------------


@dataclass
class PricingContextEvent(ModuleDomainEvent, abstract=True):
    """Intermediate base for all pricing-context domain events."""

    aggregate_type: str = "pricing_context"


@dataclass
class PricingContextCreatedEvent(
    PricingContextEvent,
    required_fields=("context_id", "code"),
    aggregate_id_field="context_id",
):
    """Emitted when a new ``PricingContext`` is created."""

    context_id: uuid.UUID | None = None
    code: str | None = None
    is_active: bool = True
    rounding_mode: str | None = None
    updated_by: uuid.UUID | None = None
    event_type: str = "PricingContextCreatedEvent"


@dataclass
class PricingContextUpdatedEvent(
    PricingContextEvent,
    required_fields=("context_id", "code"),
    aggregate_id_field="context_id",
):
    """Emitted when mutable fields of a ``PricingContext`` change."""

    context_id: uuid.UUID | None = None
    code: str | None = None
    rounding_mode: str | None = None
    rounding_step: str | None = None
    margin_floor_pct: str | None = None
    evaluation_timeout_ms: int | None = None
    simulation_threshold: int | None = None
    approval_required_on_publish: bool = False
    range_base_variable_code: str | None = None
    name: dict[str, str] = field(default_factory=dict)
    updated_by: uuid.UUID | None = None
    event_type: str = "PricingContextUpdatedEvent"


@dataclass
class PricingContextFrozenEvent(
    PricingContextEvent,
    required_fields=("context_id", "code", "freeze_reason"),
    aggregate_id_field="context_id",
):
    """Emitted when a context is put into the frozen state."""

    context_id: uuid.UUID | None = None
    code: str | None = None
    freeze_reason: str | None = None
    updated_by: uuid.UUID | None = None
    event_type: str = "PricingContextFrozenEvent"


@dataclass
class PricingContextUnfrozenEvent(
    PricingContextEvent,
    required_fields=("context_id", "code"),
    aggregate_id_field="context_id",
):
    """Emitted when a context is unfrozen."""

    context_id: uuid.UUID | None = None
    code: str | None = None
    updated_by: uuid.UUID | None = None
    event_type: str = "PricingContextUnfrozenEvent"


@dataclass
class PricingContextDeactivatedEvent(
    PricingContextEvent,
    required_fields=("context_id", "code"),
    aggregate_id_field="context_id",
):
    """Emitted when a context is soft-deactivated (``is_active=false``)."""

    context_id: uuid.UUID | None = None
    code: str | None = None
    updated_by: uuid.UUID | None = None
    event_type: str = "PricingContextDeactivatedEvent"


@dataclass
class PricingContextGlobalValueSetEvent(
    PricingContextEvent,
    required_fields=("context_id", "code", "variable_code"),
    aggregate_id_field="context_id",
):
    """Emitted when a global-scope variable value is set/updated on a context."""

    context_id: uuid.UUID | None = None
    code: str | None = None
    variable_code: str | None = None
    updated_by: uuid.UUID | None = None
    event_type: str = "PricingContextGlobalValueSetEvent"


# ---------------------------------------------------------------------------
# Formula version events
# ---------------------------------------------------------------------------


@dataclass
class FormulaVersionEvent(ModuleDomainEvent, abstract=True):
    """Intermediate base for all formula-version domain events."""

    aggregate_type: str = "pricing_formula_version"


@dataclass
class FormulaDraftSavedEvent(
    FormulaVersionEvent,
    required_fields=("version_id", "context_id", "version_number"),
    aggregate_id_field="version_id",
):
    """Emitted when a draft AST is created or updated."""

    version_id: uuid.UUID | None = None
    context_id: uuid.UUID | None = None
    version_number: int | None = None
    updated_by: uuid.UUID | None = None
    event_type: str = "FormulaDraftSavedEvent"


@dataclass
class FormulaDraftDiscardedEvent(
    FormulaVersionEvent,
    required_fields=("version_id", "context_id"),
    aggregate_id_field="version_id",
):
    """Emitted when a draft is discarded (DELETE /formula/draft)."""

    version_id: uuid.UUID | None = None
    context_id: uuid.UUID | None = None
    version_number: int | None = None
    updated_by: uuid.UUID | None = None
    event_type: str = "FormulaDraftDiscardedEvent"


@dataclass
class FormulaPublishedEvent(
    FormulaVersionEvent,
    required_fields=("version_id", "context_id", "version_number"),
    aggregate_id_field="version_id",
):
    """Emitted when a draft transitions to published (FRD §FormulaVersion FSM)."""

    version_id: uuid.UUID | None = None
    context_id: uuid.UUID | None = None
    version_number: int | None = None
    previous_version_id: uuid.UUID | None = None
    published_by: uuid.UUID | None = None
    event_type: str = "FormulaPublishedEvent"


@dataclass
class FormulaRolledBackEvent(
    FormulaVersionEvent,
    required_fields=("version_id", "context_id", "version_number"),
    aggregate_id_field="version_id",
):
    """Emitted when an archived version is restored as published."""

    version_id: uuid.UUID | None = None
    context_id: uuid.UUID | None = None
    version_number: int | None = None
    rolled_back_from_version_id: uuid.UUID | None = None
    updated_by: uuid.UUID | None = None
    event_type: str = "FormulaRolledBackEvent"


# ---------------------------------------------------------------------------
# Category pricing settings events
# ---------------------------------------------------------------------------


@dataclass
class CategoryPricingSettingsEvent(ModuleDomainEvent, abstract=True):
    """Intermediate base for ``CategoryPricingSettings`` domain events."""

    aggregate_type: str = "pricing_category_settings"


@dataclass
class CategoryPricingSettingsCreatedEvent(
    CategoryPricingSettingsEvent,
    required_fields=("settings_id", "category_id", "context_id"),
    aggregate_id_field="settings_id",
):
    """Emitted when new settings are created for (category_id, context_id)."""

    settings_id: uuid.UUID | None = None
    category_id: uuid.UUID | None = None
    context_id: uuid.UUID | None = None
    values: dict[str, str] = field(default_factory=dict)
    explicit_no_ranges: bool = False
    range_count: int = 0
    updated_by: uuid.UUID | None = None
    event_type: str = "CategoryPricingSettingsCreatedEvent"


@dataclass
class CategoryPricingSettingsUpdatedEvent(
    CategoryPricingSettingsEvent,
    required_fields=("settings_id", "category_id", "context_id"),
    aggregate_id_field="settings_id",
):
    """Emitted when values or ranges on existing settings change."""

    settings_id: uuid.UUID | None = None
    category_id: uuid.UUID | None = None
    context_id: uuid.UUID | None = None
    values: dict[str, str] = field(default_factory=dict)
    explicit_no_ranges: bool = False
    range_count: int = 0
    updated_by: uuid.UUID | None = None
    event_type: str = "CategoryPricingSettingsUpdatedEvent"


@dataclass
class CategoryPricingSettingsDeletedEvent(
    CategoryPricingSettingsEvent,
    required_fields=("settings_id", "category_id", "context_id"),
    aggregate_id_field="settings_id",
):
    """Emitted when settings are removed for (category_id, context_id)."""

    settings_id: uuid.UUID | None = None
    category_id: uuid.UUID | None = None
    context_id: uuid.UUID | None = None
    updated_by: uuid.UUID | None = None
    event_type: str = "CategoryPricingSettingsDeletedEvent"


# ---------------------------------------------------------------------------
# Supplier-type → context mapping
# ---------------------------------------------------------------------------


@dataclass
class SupplierTypeContextMappingEvent(ModuleDomainEvent, abstract=True):
    """Intermediate base for ``SupplierTypeContextMapping`` events."""

    aggregate_type: str = "pricing_supplier_type_context_mapping"


@dataclass
class SupplierTypeContextMappingCreatedEvent(
    SupplierTypeContextMappingEvent,
    required_fields=("mapping_id", "supplier_type", "context_id"),
    aggregate_id_field="mapping_id",
):
    """Emitted when a mapping is first created for a supplier_type."""

    mapping_id: uuid.UUID | None = None
    supplier_type: str | None = None
    context_id: uuid.UUID | None = None
    updated_by: uuid.UUID | None = None
    event_type: str = "SupplierTypeContextMappingCreatedEvent"


@dataclass
class SupplierTypeContextMappingUpdatedEvent(
    SupplierTypeContextMappingEvent,
    required_fields=("mapping_id", "supplier_type", "context_id"),
    aggregate_id_field="mapping_id",
):
    """Emitted when an existing mapping's context_id changes."""

    mapping_id: uuid.UUID | None = None
    supplier_type: str | None = None
    context_id: uuid.UUID | None = None
    previous_context_id: uuid.UUID | None = None
    updated_by: uuid.UUID | None = None
    event_type: str = "SupplierTypeContextMappingUpdatedEvent"


@dataclass
class SupplierTypeContextMappingDeletedEvent(
    SupplierTypeContextMappingEvent,
    required_fields=("mapping_id", "supplier_type"),
    aggregate_id_field="mapping_id",
):
    """Emitted when a mapping is removed."""

    mapping_id: uuid.UUID | None = None
    supplier_type: str | None = None
    context_id: uuid.UUID | None = None
    updated_by: uuid.UUID | None = None
    event_type: str = "SupplierTypeContextMappingDeletedEvent"


# ---------------------------------------------------------------------------
# Supplier pricing settings
# ---------------------------------------------------------------------------


@dataclass
class SupplierPricingSettingsEvent(ModuleDomainEvent, abstract=True):
    """Intermediate base for ``SupplierPricingSettings`` domain events."""

    aggregate_type: str = "pricing_supplier_settings"


@dataclass
class SupplierPricingSettingsCreatedEvent(
    SupplierPricingSettingsEvent,
    required_fields=("settings_id", "supplier_id"),
    aggregate_id_field="settings_id",
):
    """Emitted when new settings are created for a supplier."""

    settings_id: uuid.UUID | None = None
    supplier_id: uuid.UUID | None = None
    values: dict[str, str] = field(default_factory=dict)
    updated_by: uuid.UUID | None = None
    event_type: str = "SupplierPricingSettingsCreatedEvent"


@dataclass
class SupplierPricingSettingsUpdatedEvent(
    SupplierPricingSettingsEvent,
    required_fields=("settings_id", "supplier_id"),
    aggregate_id_field="settings_id",
):
    """Emitted when values on existing supplier settings change."""

    settings_id: uuid.UUID | None = None
    supplier_id: uuid.UUID | None = None
    values: dict[str, str] = field(default_factory=dict)
    updated_by: uuid.UUID | None = None
    event_type: str = "SupplierPricingSettingsUpdatedEvent"


@dataclass
class SupplierPricingSettingsDeletedEvent(
    SupplierPricingSettingsEvent,
    required_fields=("settings_id", "supplier_id"),
    aggregate_id_field="settings_id",
):
    """Emitted when supplier settings are removed."""

    settings_id: uuid.UUID | None = None
    supplier_id: uuid.UUID | None = None
    updated_by: uuid.UUID | None = None
    event_type: str = "SupplierPricingSettingsDeletedEvent"
