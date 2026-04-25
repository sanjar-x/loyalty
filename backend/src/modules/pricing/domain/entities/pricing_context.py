"""``PricingContext`` aggregate — configuration of a pricing pipeline.

A ``PricingContext`` scopes everything downstream: formula versions are bound
to a context, category settings/ranges are stored per-context, and each
``ProductPricingProfile`` resolves to exactly one active context.

Immutable-after-create: ``code``.

State flags:
- ``is_active``  — a deactivated context is hidden from UI and cannot be
  assigned to new products. Existing references continue to work until
  migrated (soft deactivation, deferred to later slices).
- ``is_frozen``  — emergency switch disabling mass recalc while investigating
  a pricing incident. Freeze requires a non-empty reason.
"""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime
from decimal import Decimal

import attrs

from src.modules.pricing.domain.events import (
    PricingContextCreatedEvent,
    PricingContextDeactivatedEvent,
    PricingContextFrozenEvent,
    PricingContextGlobalValueSetEvent,
    PricingContextUnfrozenEvent,
    PricingContextUpdatedEvent,
)
from src.modules.pricing.domain.exceptions import PricingContextValidationError
from src.modules.pricing.domain.value_objects import RoundingMode
from src.shared.interfaces.entities import AggregateRoot

_CONTEXT_CODE_RE = re.compile(r"^[a-z][a-z0-9_]{1,63}$")
_VARIABLE_CODE_RE = re.compile(r"^[a-z][a-z0-9_]{1,63}$")
_LANG_TAGS = frozenset({"ru", "en"})
_TIMEOUT_MS_MIN = 1
_TIMEOUT_MS_MAX = 60_000
_MARGIN_FLOOR_MIN = Decimal("0")
_MARGIN_FLOOR_MAX = Decimal("1")


def _validate_code(code: str) -> None:
    if not isinstance(code, str) or not _CONTEXT_CODE_RE.fullmatch(code):
        raise PricingContextValidationError(
            message=f"Invalid context code: {code!r}. Expected /^[a-z][a-z0-9_]{{1,63}}$/.",
            error_code="PRICING_CONTEXT_CODE_INVALID",
            details={"code": code},
        )


def _validate_i18n(field_name: str, value: dict[str, str]) -> None:
    if not isinstance(value, dict) or not value:
        raise PricingContextValidationError(
            message=f"{field_name} must be a non-empty i18n mapping.",
            error_code="PRICING_CONTEXT_I18N_EMPTY",
            details={"field": field_name},
        )
    for required in _LANG_TAGS:
        text = value.get(required)
        if not isinstance(text, str) or not text.strip():
            raise PricingContextValidationError(
                message=f"{field_name} must include a non-empty {required!r} translation.",
                error_code="PRICING_CONTEXT_I18N_MISSING",
                details={"field": field_name, "missing_lang": required},
            )
    for lang in value:
        if lang not in _LANG_TAGS and not re.fullmatch(r"[a-z]{2}(?:-[A-Z]{2})?", lang):
            raise PricingContextValidationError(
                message=f"{field_name} has invalid language tag {lang!r}.",
                error_code="PRICING_CONTEXT_I18N_BAD_LANG",
                details={"field": field_name, "lang": lang},
            )


def _validate_rounding_step(rounding_step: Decimal) -> None:
    if not isinstance(rounding_step, Decimal):
        raise PricingContextValidationError(
            message="rounding_step must be a Decimal.",
            error_code="PRICING_CONTEXT_ROUNDING_STEP_TYPE",
        )
    if not rounding_step.is_finite() or rounding_step <= 0:
        raise PricingContextValidationError(
            message=f"rounding_step must be > 0 (got {rounding_step}).",
            error_code="PRICING_CONTEXT_ROUNDING_STEP_INVALID",
            details={"rounding_step": str(rounding_step)},
        )


def _validate_margin_floor(margin_floor_pct: Decimal) -> None:
    if not isinstance(margin_floor_pct, Decimal):
        raise PricingContextValidationError(
            message="margin_floor_pct must be a Decimal.",
            error_code="PRICING_CONTEXT_MARGIN_FLOOR_TYPE",
        )
    if (
        not margin_floor_pct.is_finite()
        or margin_floor_pct < _MARGIN_FLOOR_MIN
        or margin_floor_pct > _MARGIN_FLOOR_MAX
    ):
        raise PricingContextValidationError(
            message=(
                f"margin_floor_pct must be within [0, 1] (got {margin_floor_pct})."
            ),
            error_code="PRICING_CONTEXT_MARGIN_FLOOR_RANGE",
            details={"margin_floor_pct": str(margin_floor_pct)},
        )


def _validate_timeout(evaluation_timeout_ms: int) -> None:
    if not isinstance(evaluation_timeout_ms, int) or isinstance(
        evaluation_timeout_ms, bool
    ):
        raise PricingContextValidationError(
            message="evaluation_timeout_ms must be an int.",
            error_code="PRICING_CONTEXT_TIMEOUT_TYPE",
        )
    if (
        evaluation_timeout_ms < _TIMEOUT_MS_MIN
        or evaluation_timeout_ms > _TIMEOUT_MS_MAX
    ):
        raise PricingContextValidationError(
            message=(
                f"evaluation_timeout_ms must be within "
                f"[{_TIMEOUT_MS_MIN}, {_TIMEOUT_MS_MAX}] ms "
                f"(got {evaluation_timeout_ms})."
            ),
            error_code="PRICING_CONTEXT_TIMEOUT_RANGE",
            details={"evaluation_timeout_ms": evaluation_timeout_ms},
        )


def _validate_simulation_threshold(simulation_threshold: int) -> None:
    if not isinstance(simulation_threshold, int) or isinstance(
        simulation_threshold, bool
    ):
        raise PricingContextValidationError(
            message="simulation_threshold must be an int.",
            error_code="PRICING_CONTEXT_SIM_THRESHOLD_TYPE",
        )
    if simulation_threshold < 0:
        raise PricingContextValidationError(
            message=(
                f"simulation_threshold must be >= 0 (got {simulation_threshold})."
            ),
            error_code="PRICING_CONTEXT_SIM_THRESHOLD_NEGATIVE",
            details={"simulation_threshold": simulation_threshold},
        )


def _validate_range_base_variable_code(code: str | None) -> None:
    if code is None:
        return
    if not isinstance(code, str) or not _VARIABLE_CODE_RE.fullmatch(code):
        raise PricingContextValidationError(
            message=(
                f"Invalid range_base_variable_code: {code!r}. "
                "Expected /^[a-z][a-z0-9_]{1,63}$/."
            ),
            error_code="PRICING_CONTEXT_RANGE_BASE_VARIABLE_CODE_INVALID",
            details={"range_base_variable_code": code},
        )


def _validate_freeze_reason(reason: str) -> None:
    if not isinstance(reason, str) or not reason.strip():
        raise PricingContextValidationError(
            message="freeze_reason must be a non-empty string.",
            error_code="PRICING_CONTEXT_FREEZE_REASON_EMPTY",
        )
    if len(reason) > 1024:
        raise PricingContextValidationError(
            message="freeze_reason is too long (max 1024 chars).",
            error_code="PRICING_CONTEXT_FREEZE_REASON_TOO_LONG",
        )


@attrs.define(kw_only=True)
class PricingContext(AggregateRoot):
    """A configuration envelope for the pricing pipeline (FRD §Contexts)."""

    id: uuid.UUID
    code: str
    name: dict[str, str] = attrs.field(factory=dict)
    is_active: bool = True
    is_frozen: bool = False
    freeze_reason: str | None = None
    rounding_mode: RoundingMode = RoundingMode.HALF_UP
    rounding_step: Decimal = attrs.field(factory=lambda: Decimal("0.01"))
    margin_floor_pct: Decimal = attrs.field(factory=lambda: Decimal("0"))
    evaluation_timeout_ms: int = 50
    simulation_threshold: int = 0
    approval_required_on_publish: bool = False
    range_base_variable_code: str | None = None
    active_formula_version_id: uuid.UUID | None = None
    global_values: dict[str, Decimal] = attrs.field(factory=dict)
    # ADR-005 — per-key set-at timestamps used by the FX-staleness gate.
    # Mirrors ``global_values`` keys; missing entries are treated as
    # "never set" by recompute consumers.
    global_values_set_at: dict[str, datetime] = attrs.field(factory=dict)
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
        name: dict[str, str],
        rounding_mode: RoundingMode = RoundingMode.HALF_UP,
        rounding_step: Decimal = Decimal("0.01"),
        margin_floor_pct: Decimal = Decimal("0"),
        evaluation_timeout_ms: int = 50,
        simulation_threshold: int = 0,
        approval_required_on_publish: bool = False,
        range_base_variable_code: str | None = None,
        actor_id: uuid.UUID,
    ) -> PricingContext:
        _validate_code(code)
        _validate_i18n("name", name)
        _validate_rounding_step(rounding_step)
        _validate_margin_floor(margin_floor_pct)
        _validate_timeout(evaluation_timeout_ms)
        _validate_simulation_threshold(simulation_threshold)
        _validate_range_base_variable_code(range_base_variable_code)

        now = datetime.now(UTC)
        ctx = cls(
            id=uuid.uuid4(),
            code=code,
            name=dict(name),
            is_active=True,
            is_frozen=False,
            freeze_reason=None,
            rounding_mode=rounding_mode,
            rounding_step=rounding_step,
            margin_floor_pct=margin_floor_pct,
            evaluation_timeout_ms=evaluation_timeout_ms,
            simulation_threshold=simulation_threshold,
            approval_required_on_publish=approval_required_on_publish,
            range_base_variable_code=range_base_variable_code,
            active_formula_version_id=None,
            global_values={},
            global_values_set_at={},
            version_lock=0,
            created_at=now,
            updated_at=now,
            updated_by=actor_id,
        )
        ctx.add_domain_event(
            PricingContextCreatedEvent(
                context_id=ctx.id,
                code=ctx.code,
                is_active=ctx.is_active,
                rounding_mode=ctx.rounding_mode.value,
                updated_by=actor_id,
            )
        )
        return ctx

    # ------------------------------------------------------------------
    # Mutators
    # ------------------------------------------------------------------

    def update(
        self,
        *,
        actor_id: uuid.UUID,
        name: dict[str, str] | None = None,
        rounding_mode: RoundingMode | None = None,
        rounding_step: Decimal | None = None,
        margin_floor_pct: Decimal | None = None,
        evaluation_timeout_ms: int | None = None,
        simulation_threshold: int | None = None,
        approval_required_on_publish: bool | None = None,
        range_base_variable_code: str | None = None,
        range_base_variable_code_provided: bool = False,
    ) -> None:
        """Patch mutable fields.

        ``range_base_variable_code_provided=True`` distinguishes "clear to None"
        from "not touched". Other nullable fields use the
        ``if arg is not None`` idiom because ``None`` means "unchanged".
        """
        if name is not None:
            _validate_i18n("name", name)
            self.name = dict(name)
        if rounding_mode is not None:
            self.rounding_mode = rounding_mode
        if rounding_step is not None:
            _validate_rounding_step(rounding_step)
            self.rounding_step = rounding_step
        if margin_floor_pct is not None:
            _validate_margin_floor(margin_floor_pct)
            self.margin_floor_pct = margin_floor_pct
        if evaluation_timeout_ms is not None:
            _validate_timeout(evaluation_timeout_ms)
            self.evaluation_timeout_ms = evaluation_timeout_ms
        if simulation_threshold is not None:
            _validate_simulation_threshold(simulation_threshold)
            self.simulation_threshold = simulation_threshold
        if approval_required_on_publish is not None:
            self.approval_required_on_publish = approval_required_on_publish
        if range_base_variable_code_provided:
            _validate_range_base_variable_code(range_base_variable_code)
            self.range_base_variable_code = range_base_variable_code

        self._touch(actor_id)
        self.add_domain_event(
            PricingContextUpdatedEvent(
                context_id=self.id,
                code=self.code,
                rounding_mode=self.rounding_mode.value,
                rounding_step=format(self.rounding_step, "f"),
                margin_floor_pct=format(self.margin_floor_pct, "f"),
                evaluation_timeout_ms=self.evaluation_timeout_ms,
                simulation_threshold=self.simulation_threshold,
                approval_required_on_publish=self.approval_required_on_publish,
                range_base_variable_code=self.range_base_variable_code,
                name=dict(self.name),
                updated_by=actor_id,
            )
        )

    def freeze(self, *, reason: str, actor_id: uuid.UUID) -> None:
        _validate_freeze_reason(reason)
        self.is_frozen = True
        self.freeze_reason = reason
        self._touch(actor_id)
        self.add_domain_event(
            PricingContextFrozenEvent(
                context_id=self.id,
                code=self.code,
                freeze_reason=reason,
                updated_by=actor_id,
            )
        )

    def unfreeze(self, *, actor_id: uuid.UUID) -> None:
        self.is_frozen = False
        self.freeze_reason = None
        self._touch(actor_id)
        self.add_domain_event(
            PricingContextUnfrozenEvent(
                context_id=self.id,
                code=self.code,
                updated_by=actor_id,
            )
        )

    def deactivate(self, *, actor_id: uuid.UUID) -> None:
        self.is_active = False
        self._touch(actor_id)
        self.add_domain_event(
            PricingContextDeactivatedEvent(
                context_id=self.id,
                code=self.code,
                updated_by=actor_id,
            )
        )

    def _touch(self, actor_id: uuid.UUID) -> None:
        self.updated_at = datetime.now(UTC)
        self.updated_by = actor_id
        self.version_lock += 1

    def set_active_formula_version(
        self,
        *,
        version_id: uuid.UUID | None,
        actor_id: uuid.UUID,
    ) -> None:
        """Update the pointer to the currently-published ``FormulaVersion``.

        Internal coupling with the Formulas slice. No domain event is emitted
        here — the Formula's own ``Published``/``RolledBack`` event covers
        the semantic meaning; this only bumps ``version_lock`` so the row is
        safely updated under optimistic locking.
        """
        self.active_formula_version_id = version_id
        self._touch(actor_id)

    def set_global_value(
        self,
        *,
        variable_code: str,
        value: Decimal,
        actor_id: uuid.UUID,
    ) -> None:
        """Store or update a ``global``-scope variable value on this context.

        The value is validated to be a finite Decimal. Variable existence and
        scope checks are performed in the application layer (the domain stores
        what it is told).
        """
        if not isinstance(value, Decimal) or not value.is_finite():
            from src.modules.pricing.domain.exceptions import (
                PricingContextValidationError,
            )

            raise PricingContextValidationError(
                message="global variable value must be a finite Decimal.",
                error_code="PRICING_CONTEXT_GLOBAL_VALUE_INVALID",
                details={"variable_code": variable_code, "value": str(value)},
            )
        now = datetime.now(UTC)
        self.global_values = {**self.global_values, variable_code: value}
        self.global_values_set_at = {
            **self.global_values_set_at,
            variable_code: now,
        }
        self._touch(actor_id)
        self.add_domain_event(
            PricingContextGlobalValueSetEvent(
                context_id=self.id,
                code=self.code,
                variable_code=variable_code,
                updated_by=actor_id,
            )
        )
