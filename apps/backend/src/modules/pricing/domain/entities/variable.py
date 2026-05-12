"""``Variable`` aggregate — registry of pricing variables.

A ``Variable`` describes *what* a named input to the pricing system means:
its code, human-readable labels, data type, unit of measurement, and *scope*
(where the value lives). Actual values are stored elsewhere according to
scope — see the scope-specific aggregates (``ProductPricingProfile``,
``CategoryPricingSettings``, ``SupplierPricingSettings``, global context
values, range buckets).

Immutable-after-create fields (enforced in the application layer on PATCH):
``code``, ``scope``, ``data_type``, ``unit``, ``is_fx_rate``.
"""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime
from decimal import Decimal

import attrs

from src.modules.pricing.domain.events import (
    VariableCreatedEvent,
    VariableDeletedEvent,
    VariableUpdatedEvent,
)
from src.modules.pricing.domain.exceptions import VariableValidationError
from src.modules.pricing.domain.value_objects import VariableDataType, VariableScope
from src.shared.interfaces.entities import AggregateRoot

_VARIABLE_CODE_RE = re.compile(r"^[a-z][a-z0-9_]{1,63}$")
_UNIT_RE = re.compile(r"^[A-Z][A-Za-z0-9_/%*]{0,31}$")
_LANG_TAGS = frozenset({"ru", "en"})
_FX_MAX_AGE_MIN = 1
_FX_MAX_AGE_MAX = 365


def _validate_code(code: str) -> None:
    if not isinstance(code, str) or not _VARIABLE_CODE_RE.fullmatch(code):
        raise VariableValidationError(
            message=f"Invalid variable code: {code!r}. Expected /^[a-z][a-z0-9_]{{1,63}}$/.",
            error_code="PRICING_VARIABLE_CODE_INVALID",
            details={"code": code},
        )


def _validate_unit(unit: str) -> None:
    """Sanity check on unit string.

    Full unit-algebra validation (RUB/CNY, dimensionless, etc.) is the
    responsibility of the formula engine slice. Here we only check that the
    unit looks like a non-empty, strictly-formatted code.
    """
    if not isinstance(unit, str) or not _UNIT_RE.fullmatch(unit):
        raise VariableValidationError(
            message=f"Invalid unit: {unit!r}.",
            error_code="PRICING_VARIABLE_UNIT_INVALID",
            details={"unit": unit},
        )


def _validate_i18n(field_name: str, mapping: dict[str, str]) -> None:
    if not isinstance(mapping, dict) or not mapping:
        raise VariableValidationError(
            message=f"{field_name} must be a non-empty i18n dict.",
            error_code="PRICING_VARIABLE_I18N_EMPTY",
            details={"field": field_name},
        )
    missing = _LANG_TAGS - mapping.keys()
    if missing:
        raise VariableValidationError(
            message=(f"{field_name} missing required languages: {sorted(missing)}"),
            error_code="PRICING_VARIABLE_I18N_MISSING_LANG",
            details={"field": field_name, "missing": sorted(missing)},
        )
    for lang, text in mapping.items():
        if not isinstance(lang, str) or not isinstance(text, str):
            raise VariableValidationError(
                message=f"{field_name} entries must be str→str.",
                error_code="PRICING_VARIABLE_I18N_INVALID_ENTRY",
                details={"field": field_name},
            )
        if lang not in _LANG_TAGS and not re.fullmatch(r"[a-z]{2}(?:-[A-Z]{2})?", lang):
            # unknown languages are allowed only in addition to required ones,
            # but they must be short ISO-like codes
            raise VariableValidationError(
                message=f"{field_name} has invalid language tag {lang!r}.",
                error_code="PRICING_VARIABLE_I18N_BAD_LANG",
                details={"field": field_name, "lang": lang},
            )
        if not text.strip():
            raise VariableValidationError(
                message=f"{field_name}[{lang!r}] must not be blank.",
                error_code="PRICING_VARIABLE_I18N_BLANK",
                details={"field": field_name, "lang": lang},
            )


def _validate_default_value(value: Decimal | None) -> None:
    if value is None:
        return
    if not isinstance(value, Decimal):
        raise VariableValidationError(
            message=(
                f"default_value must be Decimal or None, got {type(value).__name__}."
            ),
            error_code="PRICING_VARIABLE_DEFAULT_TYPE",
            details={"type": type(value).__name__},
        )
    if not value.is_finite():
        raise VariableValidationError(
            message="default_value must be finite.",
            error_code="PRICING_VARIABLE_DEFAULT_NON_FINITE",
        )


def _validate_fx_rules(
    *,
    is_fx_rate: bool,
    data_type: VariableDataType,
    max_age_days: int | None,
) -> None:
    if not is_fx_rate:
        if max_age_days is not None:
            raise VariableValidationError(
                message="max_age_days is only allowed when is_fx_rate=True.",
                error_code="PRICING_VARIABLE_MAX_AGE_NOT_ALLOWED",
            )
        return
    if data_type is not VariableDataType.DECIMAL:
        raise VariableValidationError(
            message="FX-rate variables must have data_type=decimal.",
            error_code="PRICING_VARIABLE_FX_DATA_TYPE",
            details={"data_type": data_type.value},
        )
    if max_age_days is None:
        raise VariableValidationError(
            message="max_age_days is required when is_fx_rate=True.",
            error_code="PRICING_VARIABLE_MAX_AGE_REQUIRED",
        )
    if (
        not isinstance(max_age_days, int)
        or isinstance(max_age_days, bool)
        or not (_FX_MAX_AGE_MIN <= max_age_days <= _FX_MAX_AGE_MAX)
    ):
        raise VariableValidationError(
            message=(
                f"max_age_days must be an integer in "
                f"[{_FX_MAX_AGE_MIN}, {_FX_MAX_AGE_MAX}]."
            ),
            error_code="PRICING_VARIABLE_MAX_AGE_RANGE",
            details={"max_age_days": max_age_days},
        )


@attrs.define(kw_only=True)
class Variable(AggregateRoot):
    """A named pricing input described in the variable registry.

    Immutable-after-create fields are guarded by the application layer; the
    domain itself exposes mutators only for the subset of fields that may
    legitimately change.
    """

    id: uuid.UUID
    code: str
    scope: VariableScope
    data_type: VariableDataType
    unit: str
    name: dict[str, str] = attrs.field(factory=dict)
    description: dict[str, str] = attrs.field(factory=dict)
    is_required: bool = False
    default_value: Decimal | None = None
    is_system: bool = False
    is_fx_rate: bool = False
    is_user_editable_at_runtime: bool = False
    max_age_days: int | None = None
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
        code: str,
        scope: VariableScope,
        data_type: VariableDataType,
        unit: str,
        name: dict[str, str],
        description: dict[str, str] | None = None,
        is_required: bool = False,
        default_value: Decimal | None = None,
        is_system: bool = False,
        is_fx_rate: bool = False,
        max_age_days: int | None = None,
        actor_id: uuid.UUID,
    ) -> Variable:
        """Register a new variable and emit a ``Created`` event."""
        _validate_code(code)
        _validate_unit(unit)
        _validate_i18n("name", name)
        description = description or {}
        if description:
            _validate_i18n("description", description)
        _validate_default_value(default_value)
        _validate_fx_rules(
            is_fx_rate=is_fx_rate,
            data_type=data_type,
            max_age_days=max_age_days,
        )

        now = datetime.now(UTC)
        variable = cls(
            id=uuid.uuid4(),
            code=code,
            scope=scope,
            data_type=data_type,
            unit=unit,
            name=dict(name),
            description=dict(description),
            is_required=is_required,
            default_value=default_value,
            is_system=is_system,
            is_fx_rate=is_fx_rate,
            is_user_editable_at_runtime=False,  # v2-reserved per FRD; always False in v1.
            max_age_days=max_age_days,
            version_lock=0,
            created_at=now,
            updated_at=now,
            updated_by=actor_id,
        )
        variable.add_domain_event(
            VariableCreatedEvent(
                variable_id=variable.id,
                code=variable.code,
                scope=variable.scope.value,
                data_type=variable.data_type.value,
                unit=variable.unit,
                is_fx_rate=variable.is_fx_rate,
                is_system=variable.is_system,
                is_required=variable.is_required,
                default_value=(
                    format(variable.default_value, "f")
                    if variable.default_value is not None
                    else None
                ),
                max_age_days=variable.max_age_days,
                updated_by=actor_id,
            )
        )
        return variable

    # ------------------------------------------------------------------
    # Mutators (only mutable fields)
    # ------------------------------------------------------------------

    def update(
        self,
        *,
        actor_id: uuid.UUID,
        name: dict[str, str] | None = None,
        description: dict[str, str] | None = None,
        is_required: bool | None = None,
        default_value: Decimal | None = None,
        default_value_provided: bool = False,
        max_age_days: int | None = None,
        max_age_days_provided: bool = False,
    ) -> None:
        """Update the mutable subset of fields.

        ``*_provided`` flags distinguish ``None`` (clear) from "not touched".
        """
        if name is not None:
            _validate_i18n("name", name)
            self.name = dict(name)
        if description is not None:
            if description:
                _validate_i18n("description", description)
            self.description = dict(description)
        if is_required is not None:
            self.is_required = is_required
        if default_value_provided:
            _validate_default_value(default_value)
            self.default_value = default_value
        if max_age_days_provided:
            # Re-validate the fx rules holistically so we don't allow fx vars
            # to drop max_age_days to None.
            _validate_fx_rules(
                is_fx_rate=self.is_fx_rate,
                data_type=self.data_type,
                max_age_days=max_age_days,
            )
            self.max_age_days = max_age_days

        self.updated_at = datetime.now(UTC)
        self.updated_by = actor_id
        self.version_lock += 1
        self.add_domain_event(
            VariableUpdatedEvent(
                variable_id=self.id,
                code=self.code,
                is_required=self.is_required,
                default_value=(
                    format(self.default_value, "f")
                    if self.default_value is not None
                    else None
                ),
                max_age_days=self.max_age_days,
                name=dict(self.name),
                description=dict(self.description),
                updated_by=actor_id,
            )
        )

    def mark_deleted(self, *, actor_id: uuid.UUID) -> None:
        """Emit a ``Deleted`` event — actual row removal is the repo's job.

        For this slice variables are hard-deleted (no soft-delete column); the
        event is still emitted so downstream consumers can react (e.g. invalidate
        caches).
        """
        self.updated_at = datetime.now(UTC)
        self.updated_by = actor_id
        self.add_domain_event(
            VariableDeletedEvent(
                variable_id=self.id,
                code=self.code,
                updated_by=actor_id,
            )
        )


__all__ = ["Variable"]
