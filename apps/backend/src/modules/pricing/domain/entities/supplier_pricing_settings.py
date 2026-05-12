"""``SupplierPricingSettings`` aggregate — per-supplier variable overrides.

Stores values for ``scope=supplier`` variables. Simpler than
``CategoryPricingSettings`` — **no ranges** (ranges are category-only per FRD).

FRD §Supplier Pricing Settings. This slice implements the minimal surface
(direct CRUD on a single ``supplier_id`` row). No cross-module FK — supplier
existence is a soft-reference enforced at application/presentation layers
per modular-monolith isolation rules.
"""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime
from decimal import Decimal

import attrs

from src.modules.pricing.domain.events import (
    SupplierPricingSettingsCreatedEvent,
    SupplierPricingSettingsDeletedEvent,
    SupplierPricingSettingsUpdatedEvent,
)
from src.modules.pricing.domain.exceptions import (
    SupplierPricingSettingsValidationError,
)
from src.shared.interfaces.entities import AggregateRoot

_VARIABLE_CODE_RE = re.compile(r"^[a-z][a-z0-9_]{1,63}$")
_MAX_VALUES = 128


def _validate_variable_code(code: str, *, field_name: str) -> None:
    if not isinstance(code, str) or not _VARIABLE_CODE_RE.fullmatch(code):
        raise SupplierPricingSettingsValidationError(
            message=(
                f"Invalid variable code in {field_name}: {code!r}. "
                "Expected /^[a-z][a-z0-9_]{1,63}$/."
            ),
            error_code="PRICING_SUPPLIER_SETTINGS_VARIABLE_CODE_INVALID",
            details={"field": field_name, "code": code},
        )


def _validate_decimal(value: Decimal, *, field_name: str) -> None:
    if not isinstance(value, Decimal):
        raise SupplierPricingSettingsValidationError(
            message=f"{field_name} must be a Decimal.",
            error_code="PRICING_SUPPLIER_SETTINGS_DECIMAL_TYPE",
            details={"field": field_name},
        )
    if not value.is_finite():
        raise SupplierPricingSettingsValidationError(
            message=f"{field_name} must be a finite Decimal.",
            error_code="PRICING_SUPPLIER_SETTINGS_DECIMAL_NOT_FINITE",
            details={"field": field_name},
        )


def _validate_values(values: dict[str, Decimal]) -> None:
    if not isinstance(values, dict):
        raise SupplierPricingSettingsValidationError(
            message="values must be a dict[str, Decimal].",
            error_code="PRICING_SUPPLIER_SETTINGS_VALUES_TYPE",
        )
    if len(values) > _MAX_VALUES:
        raise SupplierPricingSettingsValidationError(
            message=f"values has too many entries (max {_MAX_VALUES}).",
            error_code="PRICING_SUPPLIER_SETTINGS_VALUES_TOO_LARGE",
            details={"count": len(values)},
        )
    for code, val in values.items():
        _validate_variable_code(code, field_name="values")
        _validate_decimal(val, field_name=f"values[{code!r}]")


@attrs.define(kw_only=True)
class SupplierPricingSettings(AggregateRoot):
    """Per-supplier pricing overrides (FRD §Supplier Pricing Settings)."""

    id: uuid.UUID
    supplier_id: uuid.UUID
    values: dict[str, Decimal] = attrs.field(factory=dict)
    version_lock: int = 0
    created_at: datetime = attrs.field(factory=lambda: datetime.now(UTC))
    updated_at: datetime = attrs.field(factory=lambda: datetime.now(UTC))
    updated_by: uuid.UUID | None = None

    @classmethod
    def create(
        cls,
        *,
        supplier_id: uuid.UUID,
        values: dict[str, Decimal],
        actor_id: uuid.UUID,
    ) -> SupplierPricingSettings:
        _validate_values(values)
        now = datetime.now(UTC)
        settings = cls(
            id=uuid.uuid4(),
            supplier_id=supplier_id,
            values=dict(values),
            version_lock=0,
            created_at=now,
            updated_at=now,
            updated_by=actor_id,
        )
        settings.add_domain_event(
            SupplierPricingSettingsCreatedEvent(
                settings_id=settings.id,
                supplier_id=settings.supplier_id,
                values={k: format(v, "f") for k, v in settings.values.items()},
                updated_by=actor_id,
            )
        )
        return settings

    def replace(
        self,
        *,
        values: dict[str, Decimal],
        actor_id: uuid.UUID,
    ) -> None:
        """Full replacement of values (PUT semantics)."""
        _validate_values(values)
        self.values = dict(values)
        self._touch(actor_id)
        self.add_domain_event(
            SupplierPricingSettingsUpdatedEvent(
                settings_id=self.id,
                supplier_id=self.supplier_id,
                values={k: format(v, "f") for k, v in self.values.items()},
                updated_by=actor_id,
            )
        )

    def mark_deleted(self, *, actor_id: uuid.UUID) -> None:
        """Emit a deletion event. The caller performs the SQL DELETE."""
        self.add_domain_event(
            SupplierPricingSettingsDeletedEvent(
                settings_id=self.id,
                supplier_id=self.supplier_id,
                updated_by=actor_id,
            )
        )

    def _touch(self, actor_id: uuid.UUID) -> None:
        self.updated_at = datetime.now(UTC)
        self.updated_by = actor_id
        self.version_lock += 1


__all__ = ["SupplierPricingSettings"]
