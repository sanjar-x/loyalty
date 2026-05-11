"""Pure-domain evaluator for pricing formula ASTs.

Given a validated ``FormulaVersion`` AST and a dict of resolved variable
values, produces a ``Decimal`` ``final_price`` plus all intermediate
component values (one per binding). No I/O; callers must resolve variables
beforehand.

Matches the node grammar enforced by :func:`_validate_ast` in
``formula.py``:

- ``{"const": "<decimal-str>"[, "unit": ...]}`` — literal. ``unit`` is ignored
  in v1 (no unit-algebra yet).
- ``{"var": "<code>"}`` — look up in ``variable_values``.
- ``{"ref": "<binding_name>"}`` — result of a previously-evaluated binding.
- ``{"op": "+|-|*|/", "args": [...]}`` — ``+``/``*`` are n-ary (≥ 2);
  ``-``/``/`` are strictly binary.
- ``{"fn": "name", "args": [...]}`` — ``min`` / ``max`` (≥ 1),
  ``abs`` (1), ``round`` / ``ceil`` / ``floor`` (1 or 2: value + digits),
  ``if`` (3: cond / then / else; cond truthy when non-zero; **both branches
  are evaluated eagerly** — no short-circuit in v1).

Rounding for ``round``/``ceil``/``floor`` uses :class:`decimal.ROUND_HALF_UP`
/ :class:`decimal.ROUND_CEILING` / :class:`decimal.ROUND_FLOOR`. The global
``Decimal`` precision is inherited from the caller's context.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import (
    ROUND_CEILING,
    ROUND_FLOOR,
    ROUND_HALF_UP,
    Decimal,
    DivisionByZero,
    InvalidOperation,
)
from typing import Any

from src.modules.pricing.domain.exceptions import FormulaEvaluationError


@dataclass(frozen=True)
class EvaluationResult:
    """Outcome of evaluating a formula AST."""

    final_price: Decimal
    components: dict[str, Decimal]


_LEGACY_FINAL_COMPONENT_CODE = "final_price"
"""v1 hard-coded the final binding's name as ``final_price``. The
evaluator keeps that as a fallback for ASTs that haven't passed
through :func:`normalize_ast_to_v2` yet (which would have hoisted a
top-level ``final_component_code``)."""


def _binding_code(binding: dict[str, Any]) -> str:
    """Return the binding identifier under v1 OR v2.

    v2 stores it as ``code``; v1 used ``component_tag`` (admin-facing)
    + ``name`` (evaluator-internal). The evaluator only needs ONE
    canonical key per binding — pick whichever exists, preferring the
    new contract.
    """
    for key in ("code", "component_tag", "name"):
        value = binding.get(key)
        if isinstance(value, str) and value:
            return value
    raise FormulaEvaluationError(
        message="Binding is missing required code / component_tag / name.",
        error_code="PRICING_FORMULA_EVALUATION_FAILED",
    )


def evaluate_formula(
    ast: dict[str, Any],
    variable_values: Mapping[str, Decimal],
) -> EvaluationResult:
    """Evaluate ``ast`` against ``variable_values``.

    Assumes the AST has already passed shape validation via ``_validate_ast``;
    structural bugs are converted into :class:`FormulaEvaluationError` for
    defence in depth.

    Reads ``final_component_code`` from the AST root (v2). Falls back
    to the hard-coded ``"final_price"`` sentinel when absent (v1 ASTs
    that bypassed normalization — shouldn't happen post-migration but
    the safety net keeps the evaluator robust to direct DB inserts).
    """
    bindings = ast.get("bindings")
    if not isinstance(bindings, list) or not bindings:
        raise FormulaEvaluationError(
            message="AST has no bindings.",
            error_code="PRICING_FORMULA_EVALUATION_FAILED",
        )

    final_component_code = ast.get("final_component_code")
    if not isinstance(final_component_code, str) or not final_component_code:
        final_component_code = _LEGACY_FINAL_COMPONENT_CODE

    components: dict[str, Decimal] = {}
    for binding in bindings:
        code = _binding_code(binding)
        value = _eval_expr(
            binding["expr"],
            variable_values=variable_values,
            components=components,
            binding_name=code,
        )
        components[code] = value

    if final_component_code not in components:
        raise FormulaEvaluationError(
            message=(
                f"Formula did not produce the {final_component_code!r} "
                "binding pointed to by final_component_code."
            ),
            error_code="PRICING_FORMULA_EVALUATION_FAILED",
        )

    final_price = components[final_component_code]
    if not final_price.is_finite():
        raise FormulaEvaluationError(
            message="final_price evaluated to a non-finite Decimal (NaN/Infinity).",
            error_code="PRICING_FINAL_PRICE_INVALID",
            details={"final_price": str(final_price)},
        )
    if final_price < Decimal("0"):
        raise FormulaEvaluationError(
            message="final_price must be non-negative.",
            error_code="PRICING_FINAL_PRICE_INVALID",
            details={"final_price": str(final_price)},
        )

    return EvaluationResult(
        final_price=final_price,
        components=components,
    )


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


def _eval_expr(
    expr: Any,
    *,
    variable_values: Mapping[str, Decimal],
    components: dict[str, Decimal],
    binding_name: str,
) -> Decimal:
    if not isinstance(expr, dict):
        raise FormulaEvaluationError(
            message=f"Expression in {binding_name!r} is not an object.",
            error_code="PRICING_FORMULA_EVALUATION_FAILED",
            details={"binding": binding_name},
        )

    if "const" in expr:
        return _to_decimal(expr["const"], binding_name=binding_name)

    if "var" in expr:
        code = expr["var"]
        if code not in variable_values:
            raise FormulaEvaluationError(
                message=f"Variable {code!r} has no value in context.",
                error_code="PRICING_VARIABLE_MISSING",
                details={"binding": binding_name, "variable": code},
            )
        return _to_decimal(variable_values[code], binding_name=binding_name)

    if "ref" in expr:
        target = expr["ref"]
        if target not in components:
            raise FormulaEvaluationError(
                message=(
                    f"Binding {binding_name!r} references {target!r} which "
                    "has not been evaluated yet."
                ),
                error_code="PRICING_FORMULA_EVALUATION_FAILED",
                details={"binding": binding_name, "ref": target},
            )
        return components[target]

    if "op" in expr:
        return _eval_op(
            expr,
            variable_values=variable_values,
            components=components,
            binding_name=binding_name,
        )

    if "fn" in expr:
        return _eval_fn(
            expr,
            variable_values=variable_values,
            components=components,
            binding_name=binding_name,
        )

    raise FormulaEvaluationError(
        message=f"Unknown expression shape in {binding_name!r}.",
        error_code="PRICING_FORMULA_EVALUATION_FAILED",
        details={"binding": binding_name},
    )


def _eval_op(
    expr: dict[str, Any],
    *,
    variable_values: Mapping[str, Decimal],
    components: dict[str, Decimal],
    binding_name: str,
) -> Decimal:
    op = expr["op"]
    args = expr.get("args") or []
    values = [
        _eval_expr(
            a,
            variable_values=variable_values,
            components=components,
            binding_name=binding_name,
        )
        for a in args
    ]

    if op in ("+", "*"):
        if len(values) < 2:
            raise FormulaEvaluationError(
                message=f"Operator {op!r} requires at least 2 args.",
                error_code="PRICING_FN_ARITY",
                details={"binding": binding_name, "op": op, "arity": len(values)},
            )
        result = values[0]
        if op == "+":
            for v in values[1:]:
                result = result + v
        else:
            for v in values[1:]:
                result = result * v
        return result

    if op in ("-", "/"):
        if len(values) != 2:
            raise FormulaEvaluationError(
                message=f"Operator {op!r} requires exactly 2 args.",
                error_code="PRICING_FN_ARITY",
                details={"binding": binding_name, "op": op, "arity": len(values)},
            )
        left, right = values
        if op == "-":
            return left - right
        if right == 0:
            raise FormulaEvaluationError(
                message="Division by zero.",
                error_code="PRICING_DIVISION_BY_ZERO",
                details={"binding": binding_name},
            )
        try:
            return left / right
        except (DivisionByZero, InvalidOperation) as exc:  # pragma: no cover
            raise FormulaEvaluationError(
                message=f"Division failed: {exc}.",
                error_code="PRICING_DIVISION_BY_ZERO",
                details={"binding": binding_name},
            ) from exc

    raise FormulaEvaluationError(
        message=f"Unknown operator {op!r}.",
        error_code="PRICING_OP_UNKNOWN",
        details={"binding": binding_name, "op": op},
    )


def _eval_fn(
    expr: dict[str, Any],
    *,
    variable_values: Mapping[str, Decimal],
    components: dict[str, Decimal],
    binding_name: str,
) -> Decimal:
    fn = expr["fn"]
    args = expr.get("args") or []

    if fn == "if":
        if len(args) != 3:
            raise FormulaEvaluationError(
                message="Function 'if' requires exactly 3 args (cond, then, else).",
                error_code="PRICING_FN_ARITY",
                details={"binding": binding_name, "fn": fn, "arity": len(args)},
            )
        cond = _eval_expr(
            args[0],
            variable_values=variable_values,
            components=components,
            binding_name=binding_name,
        )
        # Eager evaluation: both branches executed. Caller must ensure both
        # branches are safe (documented limitation in v1).
        then_v = _eval_expr(
            args[1],
            variable_values=variable_values,
            components=components,
            binding_name=binding_name,
        )
        else_v = _eval_expr(
            args[2],
            variable_values=variable_values,
            components=components,
            binding_name=binding_name,
        )
        return then_v if cond != 0 else else_v

    values = [
        _eval_expr(
            a,
            variable_values=variable_values,
            components=components,
            binding_name=binding_name,
        )
        for a in args
    ]

    if fn in ("min", "max"):
        if not values:
            raise FormulaEvaluationError(
                message=f"Function {fn!r} requires at least 1 arg.",
                error_code="PRICING_FN_ARITY",
                details={"binding": binding_name, "fn": fn, "arity": 0},
            )
        return min(values) if fn == "min" else max(values)

    if fn == "abs":
        if len(values) != 1:
            raise FormulaEvaluationError(
                message="Function 'abs' requires exactly 1 arg.",
                error_code="PRICING_FN_ARITY",
                details={"binding": binding_name, "fn": fn, "arity": len(values)},
            )
        return abs(values[0])

    if fn in ("round", "ceil", "floor"):
        if len(values) not in (1, 2):
            raise FormulaEvaluationError(
                message=f"Function {fn!r} requires 1 or 2 args.",
                error_code="PRICING_FN_ARITY",
                details={"binding": binding_name, "fn": fn, "arity": len(values)},
            )
        value = values[0]
        digits = int(values[1]) if len(values) == 2 else 0
        # quantize target: 10^-digits (e.g. digits=2 → "0.01")
        if digits >= 0:
            quant = Decimal(1).scaleb(-digits)
        else:
            quant = Decimal(1).scaleb(-digits)  # positive exp, same API
        rounding_mode = {
            "round": ROUND_HALF_UP,
            "ceil": ROUND_CEILING,
            "floor": ROUND_FLOOR,
        }[fn]
        try:
            return value.quantize(quant, rounding=rounding_mode)
        except InvalidOperation as exc:
            raise FormulaEvaluationError(
                message=f"{fn!r} failed: {exc}.",
                error_code="PRICING_FORMULA_EVALUATION_FAILED",
                details={"binding": binding_name, "fn": fn},
            ) from exc

    raise FormulaEvaluationError(
        message=f"Unknown function {fn!r}.",
        error_code="PRICING_FN_UNKNOWN",
        details={"binding": binding_name, "fn": fn},
    )


def _to_decimal(value: Any, *, binding_name: str) -> Decimal:
    if isinstance(value, Decimal):
        return value
    if isinstance(value, bool):
        # bool is int subclass; reject outright to avoid silent 0/1 coercion.
        raise FormulaEvaluationError(
            message="Boolean values are not valid decimals.",
            error_code="PRICING_VALUE_NOT_DECIMAL",
            details={"binding": binding_name},
        )
    if isinstance(value, (int, str)):
        try:
            return Decimal(value)
        except (InvalidOperation, ValueError) as exc:
            raise FormulaEvaluationError(
                message=f"Cannot convert {value!r} to Decimal.",
                error_code="PRICING_VALUE_NOT_DECIMAL",
                details={"binding": binding_name, "value": str(value)},
            ) from exc
    raise FormulaEvaluationError(
        message=f"Unsupported value type {type(value).__name__!r}.",
        error_code="PRICING_VALUE_NOT_DECIMAL",
        details={"binding": binding_name, "value": str(value)},
    )


__all__ = ["EvaluationResult", "evaluate_formula"]
