"""Value objects for the pricing bounded context."""

from __future__ import annotations

from enum import Enum


class ProfileStatus(str, Enum):
    """Lifecycle status of a ``ProductPricingProfile``.

    - ``draft``: values present but not yet validated as ready for pricing.
    - ``ready``: all required variables populated; eligible for calculation.
    - ``stale``: context inputs changed (category/supplier) and profile must be re-reviewed.
    """

    DRAFT = "draft"
    READY = "ready"
    STALE = "stale"


class VariableScope(str, Enum):
    """Where the value of a ``Variable`` lives. Immutable after create.

    - ``global``: single value per pricing context (e.g. FX rate).
    - ``supplier``: value per supplier (e.g. commission %).
    - ``category``: value per category node (inherited up-tree).
    - ``range``: value per category range bucket (e.g. logistics cost bracket).
    - ``product_input``: value per product (owned by ``ProductPricingProfile``; ADR-004).
    """

    GLOBAL = "global"
    SUPPLIER = "supplier"
    CATEGORY = "category"
    RANGE = "range"
    PRODUCT_INPUT = "product_input"


class VariableDataType(str, Enum):
    """Data type of a ``Variable`` value. Immutable after create."""

    DECIMAL = "decimal"
    INTEGER = "integer"
    PERCENT = "percent"


class RoundingMode(str, Enum):
    """Supported rounding modes for pricing context (FRD §Contexts)."""

    HALF_UP = "HALF_UP"
    HALF_EVEN = "HALF_EVEN"
    CEILING = "CEILING"
    FLOOR = "FLOOR"


class FormulaStatus(str, Enum):
    """Lifecycle status of a ``FormulaVersion`` (FRD §FormulaVersion FSM).

    - ``draft``: mutable AST being edited; at most one per context.
    - ``published``: active, immutable; exactly one per context with a non-null
      ``PricingContext.active_formula_version_id``.
    - ``archived``: previously published; kept for history/rollback.
    """

    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"
