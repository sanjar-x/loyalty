"""``CategoryPricingSettings`` aggregate — per-(category, context) overrides.

Stores values for ``scope=category`` variables and a list of non-overlapping,
non-gapped ``RangeBucket`` entries used by ``scope=range`` variables.

This slice implements the *minimal* surface (FRD §Category Pricing Settings):
direct CRUD on a single (category_id, context_id) pair. Parent-category
inheritance resolution (BR-2) and ``pricing_context_override_id`` on Category
are deferred to later slices.
"""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime
from decimal import Decimal

import attrs

from src.modules.pricing.domain.events import (
    CategoryPricingSettingsCreatedEvent,
    CategoryPricingSettingsDeletedEvent,
    CategoryPricingSettingsUpdatedEvent,
)
from src.modules.pricing.domain.exceptions import (
    CategoryPricingSettingsValidationError,
)
from src.shared.interfaces.entities import AggregateRoot

_VARIABLE_CODE_RE = re.compile(r"^[a-z][a-z0-9_]{1,63}$")
_MAX_RANGES = 64
_MAX_VALUES = 128


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------


def _validate_variable_code(code: str, *, field_name: str) -> None:
    if not isinstance(code, str) or not _VARIABLE_CODE_RE.fullmatch(code):
        raise CategoryPricingSettingsValidationError(
            message=(
                f"Invalid variable code in {field_name}: {code!r}. "
                "Expected /^[a-z][a-z0-9_]{1,63}$/."
            ),
            error_code="PRICING_CATEGORY_SETTINGS_VARIABLE_CODE_INVALID",
            details={"field": field_name, "code": code},
        )


def _validate_decimal(value: Decimal, *, field_name: str) -> None:
    if not isinstance(value, Decimal):
        raise CategoryPricingSettingsValidationError(
            message=f"{field_name} must be a Decimal.",
            error_code="PRICING_CATEGORY_SETTINGS_DECIMAL_TYPE",
            details={"field": field_name},
        )
    if not value.is_finite():
        raise CategoryPricingSettingsValidationError(
            message=f"{field_name} must be a finite Decimal.",
            error_code="PRICING_CATEGORY_SETTINGS_DECIMAL_NOT_FINITE",
            details={"field": field_name},
        )


def _validate_values(values: dict[str, Decimal]) -> None:
    if not isinstance(values, dict):
        raise CategoryPricingSettingsValidationError(
            message="values must be a dict[str, Decimal].",
            error_code="PRICING_CATEGORY_SETTINGS_VALUES_TYPE",
        )
    if len(values) > _MAX_VALUES:
        raise CategoryPricingSettingsValidationError(
            message=f"values has too many entries (max {_MAX_VALUES}).",
            error_code="PRICING_CATEGORY_SETTINGS_VALUES_TOO_LARGE",
            details={"count": len(values)},
        )
    for code, val in values.items():
        _validate_variable_code(code, field_name="values")
        _validate_decimal(val, field_name=f"values[{code!r}]")


# ---------------------------------------------------------------------------
# Range bucket value object
# ---------------------------------------------------------------------------


@attrs.frozen(kw_only=True)
class RangeBucket:
    """An immutable range bucket: ``[min, max)`` with variable overrides.

    ``max=None`` means unbounded on the right (only permitted for the last
    bucket after sorting).
    """

    id: uuid.UUID
    min: Decimal
    max: Decimal | None
    values: dict[str, Decimal]

    def __attrs_post_init__(self) -> None:
        _validate_decimal(self.min, field_name="range.min")
        if self.min < 0:
            raise CategoryPricingSettingsValidationError(
                message=f"range.min must be >= 0 (got {self.min}).",
                error_code="PRICING_CATEGORY_SETTINGS_RANGE_MIN_NEGATIVE",
                details={"min": str(self.min)},
            )
        if self.max is not None:
            _validate_decimal(self.max, field_name="range.max")
            if self.max <= self.min:
                raise CategoryPricingSettingsValidationError(
                    message=(
                        f"range.max must be > range.min "
                        f"(min={self.min}, max={self.max})."
                    ),
                    error_code="PRICING_CATEGORY_SETTINGS_RANGE_MAX_LE_MIN",
                    details={"min": str(self.min), "max": str(self.max)},
                )
        _validate_values(self.values)


def _validate_ranges(
    ranges: list[RangeBucket],
    *,
    explicit_no_ranges: bool,
) -> None:
    if not isinstance(ranges, list):
        raise CategoryPricingSettingsValidationError(
            message="ranges must be a list[RangeBucket].",
            error_code="PRICING_CATEGORY_SETTINGS_RANGES_TYPE",
        )
    if explicit_no_ranges and ranges:
        raise CategoryPricingSettingsValidationError(
            message="explicit_no_ranges=true requires ranges to be empty.",
            error_code="PRICING_CATEGORY_SETTINGS_EXPLICIT_NO_RANGES_CONFLICT",
            details={"ranges_count": len(ranges)},
        )
    if len(ranges) > _MAX_RANGES:
        raise CategoryPricingSettingsValidationError(
            message=f"Too many ranges (max {_MAX_RANGES}).",
            error_code="PRICING_CATEGORY_SETTINGS_RANGES_TOO_MANY",
            details={"count": len(ranges)},
        )
    if not ranges:
        return

    # Uniqueness of bucket ids.
    ids_seen: set[uuid.UUID] = set()
    for bucket in ranges:
        if not isinstance(bucket, RangeBucket):
            raise CategoryPricingSettingsValidationError(
                message="each range entry must be a RangeBucket.",
                error_code="PRICING_CATEGORY_SETTINGS_RANGE_ITEM_TYPE",
            )
        if bucket.id in ids_seen:
            raise CategoryPricingSettingsValidationError(
                message=f"Duplicate range id {bucket.id}.",
                error_code="PRICING_CATEGORY_SETTINGS_RANGE_DUPLICATE_ID",
                details={"range_id": str(bucket.id)},
            )
        ids_seen.add(bucket.id)

    sorted_ranges = sorted(ranges, key=lambda r: r.min)
    if sorted_ranges != ranges:
        raise CategoryPricingSettingsValidationError(
            message="ranges must be sorted ascending by 'min'.",
            error_code="PRICING_CATEGORY_SETTINGS_RANGES_NOT_SORTED",
        )

    for i, bucket in enumerate(ranges):
        is_last = i == len(ranges) - 1
        if bucket.max is None and not is_last:
            raise CategoryPricingSettingsValidationError(
                message=(
                    "Only the last range may have max=null "
                    f"(index {i}, range_id={bucket.id})."
                ),
                error_code="PRICING_CATEGORY_SETTINGS_RANGE_OPEN_NOT_LAST",
                details={"index": i, "range_id": str(bucket.id)},
            )
        if i == 0:
            continue
        prev = ranges[i - 1]
        assert prev.max is not None  # previous cannot be unbounded (not last)
        if bucket.min != prev.max:
            raise CategoryPricingSettingsValidationError(
                message=(
                    f"Ranges must be contiguous (no gaps / no overlaps): "
                    f"index {i - 1}.max={prev.max} != index {i}.min={bucket.min}."
                ),
                error_code="PRICING_CATEGORY_SETTINGS_RANGES_NOT_CONTIGUOUS",
                details={
                    "prev_max": str(prev.max),
                    "curr_min": str(bucket.min),
                    "index": i,
                },
            )


# ---------------------------------------------------------------------------
# Aggregate
# ---------------------------------------------------------------------------


@attrs.define(kw_only=True)
class CategoryPricingSettings(AggregateRoot):
    """Per-(category, context) pricing overrides (FRD §Category Pricing Settings)."""

    id: uuid.UUID
    category_id: uuid.UUID
    context_id: uuid.UUID
    values: dict[str, Decimal] = attrs.field(factory=dict)
    ranges: list[RangeBucket] = attrs.field(factory=list)
    explicit_no_ranges: bool = False
    version_lock: int = 0
    created_at: datetime = attrs.field(factory=lambda: datetime.now(UTC))
    updated_at: datetime = attrs.field(factory=lambda: datetime.now(UTC))
    updated_by: uuid.UUID | None = None

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def create(
        cls,
        *,
        category_id: uuid.UUID,
        context_id: uuid.UUID,
        values: dict[str, Decimal],
        ranges: list[RangeBucket],
        explicit_no_ranges: bool,
        actor_id: uuid.UUID,
    ) -> CategoryPricingSettings:
        _validate_values(values)
        _validate_ranges(ranges, explicit_no_ranges=explicit_no_ranges)

        now = datetime.now(UTC)
        settings = cls(
            id=uuid.uuid4(),
            category_id=category_id,
            context_id=context_id,
            values=dict(values),
            ranges=list(ranges),
            explicit_no_ranges=explicit_no_ranges,
            version_lock=0,
            created_at=now,
            updated_at=now,
            updated_by=actor_id,
        )
        settings.add_domain_event(
            CategoryPricingSettingsCreatedEvent(
                settings_id=settings.id,
                category_id=settings.category_id,
                context_id=settings.context_id,
                values={k: format(v, "f") for k, v in settings.values.items()},
                explicit_no_ranges=settings.explicit_no_ranges,
                range_count=len(settings.ranges),
                updated_by=actor_id,
            )
        )
        return settings

    # ------------------------------------------------------------------
    # Mutators
    # ------------------------------------------------------------------

    def replace(
        self,
        *,
        values: dict[str, Decimal],
        ranges: list[RangeBucket],
        explicit_no_ranges: bool,
        actor_id: uuid.UUID,
    ) -> None:
        """Full replacement of values + ranges + flag (PUT semantics)."""
        _validate_values(values)
        _validate_ranges(ranges, explicit_no_ranges=explicit_no_ranges)

        self.values = dict(values)
        self.ranges = list(ranges)
        self.explicit_no_ranges = explicit_no_ranges
        self._touch(actor_id)
        self.add_domain_event(
            CategoryPricingSettingsUpdatedEvent(
                settings_id=self.id,
                category_id=self.category_id,
                context_id=self.context_id,
                values={k: format(v, "f") for k, v in self.values.items()},
                explicit_no_ranges=self.explicit_no_ranges,
                range_count=len(self.ranges),
                updated_by=actor_id,
            )
        )

    def mark_deleted(self, *, actor_id: uuid.UUID) -> None:
        """Emit a deletion event. The caller performs the SQL DELETE."""
        self.add_domain_event(
            CategoryPricingSettingsDeletedEvent(
                settings_id=self.id,
                category_id=self.category_id,
                context_id=self.context_id,
                updated_by=actor_id,
            )
        )

    def _touch(self, actor_id: uuid.UUID) -> None:
        self.updated_at = datetime.now(UTC)
        self.updated_by = actor_id
        self.version_lock += 1
