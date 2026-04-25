"""Pure-domain SKU pricing recompute (ADR-005).

Given a :class:`SkuPricingInputs` snapshot from catalog and a
:class:`SkuPricingScopeSnapshot` from pricing, produces either:

* :class:`SkuPricingComputed` — a successful pricing result with a
  deterministic ``inputs_hash``, ready to land via
  :class:`ISkuPricingResultWriter.apply_success`.
* :class:`SkuPricingFailed` — a failure status (``stale_fx`` /
  ``missing_purchase_price`` / ``formula_error``) with an admin-readable
  reason.

The function is **pure**: zero I/O, no asyncio. The context-side time
budget for formula evaluation is enforced by the orchestrating service
via ``asyncio.wait_for``; this module just calls the synchronous
``evaluate_formula`` helper.

Currency conversion is implicit through the formula AST: callers are
expected to author formulas like::

    if(purchase_price_cny > 0,
       purchase_price_cny * fx_cny_rub,
       purchase_price_rub) * (1 + supplier_margin_pct / 100)

The recompute pipeline injects the right ``purchase_price_*`` variable
based on ``SkuPricingInputs.purchase_currency`` and validates FX
freshness before calling the evaluator.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_EVEN, ROUND_HALF_UP, Decimal

from src.modules.pricing.domain.exceptions import FormulaEvaluationError
from src.modules.pricing.domain.formula_evaluator import evaluate_formula
from src.modules.pricing.domain.interfaces import (
    SkuPricingInputs,
    SkuPricingScopeSnapshot,
)
from src.modules.pricing.domain.value_objects import RoundingMode, VariableScope

# Variable codes seeded as system variables for SKU purchase price
# (see ADR-005). The resolver routes them to ``SkuPricingInputs``.
PURCHASE_PRICE_RUB_CODE = "purchase_price_rub"
PURCHASE_PRICE_CNY_CODE = "purchase_price_cny"
FX_CNY_RUB_CODE = "fx_cny_rub"


@dataclass(frozen=True)
class SkuPricingComputed:
    """Successful recompute output."""

    selling_price: Decimal
    selling_currency: str
    inputs_hash: str
    formula_version_id: uuid.UUID
    components: dict[str, Decimal]


@dataclass(frozen=True)
class SkuPricingFailed:
    """Failed recompute output (status + admin-readable reason)."""

    status: str  # one of: stale_fx, missing_purchase_price, formula_error
    reason: str


def recompute_sku_pricing(
    inputs: SkuPricingInputs,
    scope: SkuPricingScopeSnapshot,
    *,
    now: datetime | None = None,
) -> SkuPricingComputed | SkuPricingFailed:
    """Pure recompute step.

    Args:
        inputs: Per-SKU inputs from catalog.
        scope: Context-scope inputs from pricing.
        now: Override "now" for deterministic FX-staleness tests. Defaults
            to ``datetime.now(UTC)``.

    Returns:
        :class:`SkuPricingComputed` on success, :class:`SkuPricingFailed`
        on a recoverable failure (missing inputs / stale FX / formula
        error). Catastrophic invariant breaks raise — they should never
        happen and indicate a wiring bug.
    """
    if inputs.purchase_price is None or inputs.purchase_currency is None:
        return SkuPricingFailed(
            status="missing_purchase_price",
            reason="SKU has no purchase price recorded",
        )

    fx_failure = _check_fx_freshness(scope, now=now or datetime.now(UTC))
    if fx_failure is not None:
        return fx_failure

    resolved = _resolve_variable_values(inputs, scope)

    try:
        evaluation = evaluate_formula(scope.formula_ast, resolved)
    except FormulaEvaluationError as exc:
        return SkuPricingFailed(
            status="formula_error",
            reason=_truncate_reason(str(exc)),
        )
    except Exception as exc:  # pragma: no cover — evaluator catches its own
        return SkuPricingFailed(
            status="formula_error",
            reason=_truncate_reason(f"{type(exc).__name__}: {exc}"),
        )

    rounded = _round(
        evaluation.final_price,
        mode=RoundingMode(scope.rounding_mode),
        step=scope.rounding_step,
    )
    if rounded <= 0:
        return SkuPricingFailed(
            status="formula_error",
            reason=(
                f"Formula yielded non-positive price ({rounded}); "
                "review formula or supplier/category settings"
            ),
        )

    inputs_hash = _compute_inputs_hash(inputs, scope)

    return SkuPricingComputed(
        selling_price=rounded,
        selling_currency=scope.target_currency,
        inputs_hash=inputs_hash,
        formula_version_id=scope.formula_version_id,
        components=evaluation.components,
    )


def _check_fx_freshness(
    scope: SkuPricingScopeSnapshot, *, now: datetime
) -> SkuPricingFailed | None:
    """Hard-fail if any referenced FX-rate variable is older than its window."""
    for variable in scope.variables:
        if not variable.is_fx_rate:
            continue
        # Only checked when the formula actually uses this rate. Keys
        # missing from ``global_value_set_at`` mean the admin hasn't
        # entered it yet — treated the same as missing for FX rates.
        if variable.code not in scope.global_values:
            return SkuPricingFailed(
                status="stale_fx",
                reason=(
                    f"FX rate {variable.code!r} is not configured on "
                    "the pricing context"
                ),
            )
        set_at = scope.global_value_set_at.get(variable.code)
        if set_at is None:
            return SkuPricingFailed(
                status="stale_fx",
                reason=(f"FX rate {variable.code!r} has no recorded set-at timestamp"),
            )
        if variable.max_age_days is None:
            continue
        age_threshold = timedelta(days=variable.max_age_days)
        if now - set_at > age_threshold:
            return SkuPricingFailed(
                status="stale_fx",
                reason=(
                    f"FX rate {variable.code!r} is older than "
                    f"{variable.max_age_days} days "
                    f"(set at {set_at.isoformat()})"
                ),
            )
    return None


def _resolve_variable_values(
    inputs: SkuPricingInputs,
    scope: SkuPricingScopeSnapshot,
) -> dict[str, Decimal]:
    """Materialise the variable-name → Decimal map fed to the evaluator."""
    resolved: dict[str, Decimal] = {}

    sku_input_value: tuple[str, Decimal] | None = None
    if inputs.purchase_price is not None and inputs.purchase_currency is not None:
        if inputs.purchase_currency == "RUB":
            sku_input_value = (PURCHASE_PRICE_RUB_CODE, inputs.purchase_price)
        elif inputs.purchase_currency == "CNY":
            sku_input_value = (PURCHASE_PRICE_CNY_CODE, inputs.purchase_price)
        else:
            raise FormulaEvaluationError(
                message=(
                    f"Unknown purchase_currency {inputs.purchase_currency!r}; "
                    "the pricing pipeline only supports RUB or CNY (ADR-005)"
                ),
                error_code="PRICING_PURCHASE_CURRENCY_UNSUPPORTED",
                details={"currency": inputs.purchase_currency},
            )

    for variable in scope.variables:
        scope_kind = variable.scope
        if scope_kind is VariableScope.SKU_INPUT:
            # Only the SKU's *active* currency variable resolves; the
            # inactive-currency SKU_INPUT variable stays absent from the
            # resolved map. Reasoning: silently substituting ``0`` for
            # the inactive currency would make a formula such as
            # ``purchase_price_cny + base_margin`` yield a plausibly-
            # positive — but wrong — price for a RUB-denominated SKU.
            # Leaving it absent forces the eager evaluator to raise
            # ``PRICING_VARIABLE_MISSING``; the recompute service then
            # records ``formula_error`` with a precise cause so the
            # admin sees the real problem (formula vs. SKU currency
            # mismatch) instead of a wrong-but-shipped selling price.
            #
            # Single-currency contexts therefore reference exactly one
            # of ``purchase_price_rub`` / ``purchase_price_cny``;
            # multi-currency contexts compute via FX in a single
            # branch authored against the active currency only.
            if sku_input_value is not None and variable.code == sku_input_value[0]:
                resolved[variable.code] = sku_input_value[1]
            elif variable.is_required:
                raise FormulaEvaluationError(
                    message=(
                        f"Required SKU_INPUT variable {variable.code!r} "
                        f"has no value (SKU currency: "
                        f"{inputs.purchase_currency})"
                    ),
                    error_code="PRICING_VARIABLE_MISSING",
                    details={
                        "variable": variable.code,
                        "scope": variable.scope.value,
                    },
                )
            continue

        if scope_kind is VariableScope.GLOBAL:
            value = scope.global_values.get(variable.code, variable.default_value)
        elif scope_kind is VariableScope.CATEGORY:
            value = scope.category_values.get(variable.code, variable.default_value)
        elif scope_kind is VariableScope.SUPPLIER:
            value = scope.supplier_values.get(variable.code, variable.default_value)
        elif scope_kind is VariableScope.PRODUCT_INPUT:
            # ProductPricingProfile is not part of the SKU recompute path.
            # Authors should migrate product-level inputs to SKU_INPUT or
            # CATEGORY; we honour ``default_value`` for now to keep
            # backward compat with existing formulas.
            value = variable.default_value
        else:  # RANGE — deferred per FRD
            value = variable.default_value

        if value is not None:
            resolved[variable.code] = value
        elif variable.is_required:
            raise FormulaEvaluationError(
                message=(
                    f"Required variable {variable.code!r} (scope="
                    f"{variable.scope.value}) has no resolved value."
                ),
                error_code="PRICING_VARIABLE_MISSING",
                details={
                    "variable": variable.code,
                    "scope": variable.scope.value,
                },
            )

    return resolved


_ROUNDING_MAP = {
    RoundingMode.HALF_UP: ROUND_HALF_UP,
    RoundingMode.HALF_EVEN: ROUND_HALF_EVEN,
    RoundingMode.CEILING: ROUND_CEILING,
    RoundingMode.FLOOR: ROUND_FLOOR,
}


def _round(value: Decimal, *, mode: RoundingMode, step: Decimal | None) -> Decimal:
    """Quantise ``value`` to ``step`` using the given mode.

    ``step`` defaults to ``0.01`` when the context didn't specify one
    (cents/kopecks precision). A non-finite or non-positive ``value``
    is returned unchanged so the caller can detect and report it.
    """
    if not value.is_finite():
        return value
    quantum = step if step is not None and step > 0 else Decimal("0.01")
    rounding = _ROUNDING_MAP[mode]
    quantised = (value / quantum).quantize(Decimal("1"), rounding=rounding) * quantum
    # Re-quantise to the quantum's exponent so ``"199.50"`` doesn't
    # become ``"199.5"`` after multiplication.
    return quantised.quantize(quantum, rounding=ROUND_HALF_EVEN)


def _compute_inputs_hash(
    inputs: SkuPricingInputs,
    scope: SkuPricingScopeSnapshot,
) -> str:
    """Deterministic SHA-256 of every value that can change the result.

    Two recomputes are guaranteed to land identical hashes iff and
    only iff the inputs they observe are bit-for-bit equal. This is
    the property that makes at-least-once outbox delivery
    exactly-once-effective at the catalog row level.
    """
    payload: dict[str, object] = {
        "sku_id": str(inputs.sku_id),
        "purchase_price": _decimal_str(inputs.purchase_price),
        "purchase_currency": inputs.purchase_currency,
        "context_id": str(scope.context_id),
        "target_currency": scope.target_currency,
        "formula_version_id": str(scope.formula_version_id),
        "formula_version_number": scope.formula_version_number,
        "rounding_mode": scope.rounding_mode,
        "rounding_step": _decimal_str(scope.rounding_step),
        "global_values": _sorted_decimal_map(scope.global_values),
        "global_value_set_at": _sorted_datetime_map(scope.global_value_set_at),
        "category_values": _sorted_decimal_map(scope.category_values),
        "supplier_values": _sorted_decimal_map(scope.supplier_values),
        "settings_versions": list(scope.settings_versions),
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _decimal_str(value: Decimal | None) -> str | None:
    return format(value, "f") if value is not None else None


def _sorted_decimal_map(mapping: dict[str, Decimal]) -> dict[str, str]:
    return {k: format(v, "f") for k, v in sorted(mapping.items())}


def _sorted_datetime_map(mapping: dict[str, datetime]) -> dict[str, str]:
    return {k: v.isoformat() for k, v in sorted(mapping.items())}


def _truncate_reason(text: str, *, max_len: int = 500) -> str:
    return text if len(text) <= max_len else text[: max_len - 1] + "…"


__all__ = [
    "FX_CNY_RUB_CODE",
    "PURCHASE_PRICE_CNY_CODE",
    "PURCHASE_PRICE_RUB_CODE",
    "SkuPricingComputed",
    "SkuPricingFailed",
    "recompute_sku_pricing",
]
