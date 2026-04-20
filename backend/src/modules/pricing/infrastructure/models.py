"""ORM models for the pricing bounded context.

Tables:
- ``pricing_product_pricing_profiles`` — scope=product_input values per product
  (ADR-004).
- ``pricing_variables`` — variable registry (FRD §Variable).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    TIMESTAMP,
    Boolean,
    CheckConstraint,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class ProductPricingProfileModel(Base):
    """Pricing inputs for a single catalog product.

    ``product_id`` is a soft-reference (no cross-module FK) per the modular
    monolith isolation rules. Uniqueness is enforced on active (non-deleted)
    rows so that soft-deleting a profile does not block re-creation.
    """

    __tablename__ = "pricing_product_pricing_profiles"
    __table_args__ = (
        Index(
            "uq_pricing_profiles_product_active",
            "product_id",
            unique=True,
            postgresql_where="is_deleted = false",
        ),
        CheckConstraint(
            "status IN ('draft', 'ready', 'stale')",
            name="ck_pricing_profiles_valid_status",
        ),
        CheckConstraint(
            "version_lock >= 0",
            name="ck_pricing_profiles_version_non_negative",
        ),
        {"comment": "scope=product_input values per product (ADR-004)"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    context_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    # Stored as JSONB; keys = variable codes, values = Decimal-as-string
    # (Decimal is serialized as string to avoid float precision loss).
    values: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="draft")
    version_lock: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    is_deleted: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class VariableModel(Base):
    """Pricing-variable registry row.

    The ``scope``, ``code``, ``data_type``, ``unit``, and ``is_fx_rate``
    columns are immutable-after-create; enforcement lives in the application
    layer because SQL cannot express "can't change after first write" cleanly.
    """

    __tablename__ = "pricing_variables"
    __table_args__ = (
        UniqueConstraint("code", name="uq_pricing_variables_code"),
        CheckConstraint(
            "scope IN ('global', 'supplier', 'category', 'range', 'product_input')",
            name="ck_pricing_variables_valid_scope",
        ),
        CheckConstraint(
            "data_type IN ('decimal', 'integer', 'percent')",
            name="ck_pricing_variables_valid_data_type",
        ),
        CheckConstraint(
            "version_lock >= 0",
            name="ck_pricing_variables_version_non_negative",
        ),
        CheckConstraint(
            "(is_fx_rate = false AND max_age_days IS NULL) OR "
            "(is_fx_rate = true AND max_age_days BETWEEN 1 AND 365)",
            name="ck_pricing_variables_fx_age",
        ),
        {"comment": "Pricing variable registry (FRD §Variable)"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    scope: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    data_type: Mapped[str] = mapped_column(String(16), nullable=False)
    unit: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    description: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )
    is_required: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    # Decimal as string in JSONB would work, but a dedicated Numeric column
    # is simpler and queryable.
    default_value: Mapped[Decimal | None] = mapped_column(
        Numeric(24, 10), nullable=True
    )
    is_system: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false", index=True
    )
    is_fx_rate: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false", index=True
    )
    is_user_editable_at_runtime: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    max_age_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    version_lock: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class PricingContextModel(Base):
    """Pricing context registry row (FRD §Contexts).

    The ``code`` column is immutable-after-create; enforcement lives in the
    application layer.
    """

    __tablename__ = "pricing_contexts"
    __table_args__ = (
        UniqueConstraint("code", name="uq_pricing_contexts_code"),
        CheckConstraint(
            "rounding_mode IN ('HALF_UP', 'HALF_EVEN', 'CEILING', 'FLOOR')",
            name="ck_pricing_contexts_valid_rounding_mode",
        ),
        CheckConstraint(
            "rounding_step > 0",
            name="ck_pricing_contexts_rounding_step_positive",
        ),
        CheckConstraint(
            "margin_floor_pct BETWEEN 0 AND 1",
            name="ck_pricing_contexts_margin_floor_pct_range",
        ),
        CheckConstraint(
            "evaluation_timeout_ms BETWEEN 1 AND 60000",
            name="ck_pricing_contexts_timeout_range",
        ),
        CheckConstraint(
            "simulation_threshold >= 0",
            name="ck_pricing_contexts_sim_threshold_non_negative",
        ),
        CheckConstraint(
            "version_lock >= 0",
            name="ck_pricing_contexts_version_non_negative",
        ),
        CheckConstraint(
            "(is_frozen = false AND freeze_reason IS NULL) OR "
            "(is_frozen = true AND freeze_reason IS NOT NULL)",
            name="ck_pricing_contexts_freeze_consistency",
        ),
        {"comment": "Pricing context registry (FRD §Contexts)"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true", index=True
    )
    is_frozen: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false", index=True
    )
    freeze_reason: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    rounding_mode: Mapped[str] = mapped_column(
        String(16), nullable=False, default="HALF_UP", server_default="HALF_UP"
    )
    rounding_step: Mapped[Decimal] = mapped_column(
        Numeric(24, 10), nullable=False, default=Decimal("0.01")
    )
    margin_floor_pct: Mapped[Decimal] = mapped_column(
        Numeric(8, 6), nullable=False, default=Decimal("0")
    )
    evaluation_timeout_ms: Mapped[int] = mapped_column(
        Integer, nullable=False, default=50, server_default="50"
    )
    simulation_threshold: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    approval_required_on_publish: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    range_base_variable_code: Mapped[str | None] = mapped_column(
        String(64), nullable=True
    )
    active_formula_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    version_lock: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class FormulaVersionModel(Base):
    """Pricing formula versions (FRD §FormulaVersion)."""

    __tablename__ = "pricing_formula_versions"
    __table_args__ = (
        Index(
            "uq_pricing_formula_draft_per_context",
            "context_id",
            unique=True,
            postgresql_where="status = 'draft'",
        ),
        Index(
            "uq_pricing_formula_published_per_context",
            "context_id",
            unique=True,
            postgresql_where="status = 'published'",
        ),
        Index(
            "uq_pricing_formula_version_number_per_context",
            "context_id",
            "version_number",
            unique=True,
        ),
        CheckConstraint(
            "status IN ('draft', 'published', 'archived')",
            name="ck_pricing_formula_valid_status",
        ),
        CheckConstraint(
            "version_number >= 1",
            name="ck_pricing_formula_version_number_positive",
        ),
        CheckConstraint(
            "version_lock >= 0",
            name="ck_pricing_formula_version_lock_non_negative",
        ),
        CheckConstraint(
            "(status = 'draft' AND published_at IS NULL AND published_by IS NULL) OR "
            "(status IN ('published', 'archived') AND published_at IS NOT NULL)",
            name="ck_pricing_formula_published_fields_consistency",
        ),
        {"comment": "Pricing formula versions (FRD §FormulaVersion)"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    context_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    ast: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    published_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    published_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    version_lock: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class CategoryPricingSettingsModel(Base):
    """Per-(category, context) pricing overrides (FRD §Category Pricing Settings).

    ``category_id`` and ``context_id`` are soft-references (no FK) per modular
    monolith isolation rules. A unique composite index enforces at most one
    settings row per (category_id, context_id).

    ``values`` is stored as JSONB ``{code: decimal-string}``; ``ranges`` is a
    JSONB array of ``{id, min, max, values}`` objects (Decimals as strings).
    """

    __tablename__ = "pricing_category_settings"
    __table_args__ = (
        UniqueConstraint(
            "category_id",
            "context_id",
            name="uq_pricing_category_settings_cat_ctx",
        ),
        CheckConstraint(
            "version_lock >= 0",
            name="ck_pricing_category_settings_version_non_negative",
        ),
        {
            "comment": "Per-(category, context) pricing overrides (FRD §Category Pricing Settings)"
        },
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    context_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    values: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )
    ranges: Mapped[list] = mapped_column(
        JSONB, nullable=False, default=list, server_default="[]"
    )
    explicit_no_ranges: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    version_lock: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class SupplierTypeContextMappingModel(Base):
    """Maps ``supplier_type → context_id`` for automatic pricing-context resolution.

    FRD §SupplierType→Context Mapping. ``context_id`` is a soft-reference (no FK)
    per modular monolith rules; existence is enforced at the application layer.
    """

    __tablename__ = "pricing_supplier_type_context_mapping"
    __table_args__ = (
        UniqueConstraint(
            "supplier_type",
            name="uq_pricing_supplier_type_context_mapping_type",
        ),
        CheckConstraint(
            "version_lock >= 0",
            name="ck_pricing_supplier_type_context_mapping_version_non_negative",
        ),
        {
            "comment": (
                "SupplierType → default pricing context (FRD §SupplierType→Context Mapping)"
            )
        },
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    supplier_type: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True
    )
    context_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    version_lock: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class SupplierPricingSettingsModel(Base):
    """Per-supplier pricing overrides (FRD §Supplier Pricing Settings).

    ``supplier_id`` is a soft-reference (no FK) per modular monolith isolation
    rules. A unique index enforces at most one settings row per supplier.
    ``values`` is stored as JSONB ``{code: decimal-string}``.
    """

    __tablename__ = "pricing_supplier_settings"
    __table_args__ = (
        UniqueConstraint(
            "supplier_id",
            name="uq_pricing_supplier_settings_supplier",
        ),
        CheckConstraint(
            "version_lock >= 0",
            name="ck_pricing_supplier_settings_version_non_negative",
        ),
        {
            "comment": (
                "Per-supplier pricing overrides (FRD §Supplier Pricing Settings)"
            )
        },
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    supplier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    values: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )
    version_lock: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
