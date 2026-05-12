"""Unit tests for the pure-domain pricing formula evaluator."""

from __future__ import annotations

from decimal import Decimal

import pytest

from src.modules.pricing.domain.exceptions import FormulaEvaluationError
from src.modules.pricing.domain.formula_evaluator import (
    EvaluationResult,
    evaluate_formula,
)


def _ast(*bindings: dict) -> dict:
    return {"version": 1, "bindings": list(bindings)}


def _b(name: str, expr: dict, tag: str = "component") -> dict:
    return {"name": name, "component_tag": tag, "expr": expr}


# ---------------------------------------------------------------------------
# Happy paths — individual node types
# ---------------------------------------------------------------------------


class TestConst:
    def test_const_string(self) -> None:
        ast = _ast(_b("final_price", {"const": "100.50"}, tag="final_price"))
        result = evaluate_formula(ast, {})
        assert result.final_price == Decimal("100.50")

    def test_const_int(self) -> None:
        ast = _ast(_b("final_price", {"const": 42}, tag="final_price"))
        assert evaluate_formula(ast, {}).final_price == Decimal("42")

    def test_const_bool_rejected(self) -> None:
        ast = _ast(_b("final_price", {"const": True}, tag="final_price"))
        with pytest.raises(FormulaEvaluationError) as exc:
            evaluate_formula(ast, {})
        assert exc.value.error_code == "PRICING_VALUE_NOT_DECIMAL"

    def test_const_invalid_string(self) -> None:
        ast = _ast(_b("final_price", {"const": "not-a-number"}, tag="final_price"))
        with pytest.raises(FormulaEvaluationError) as exc:
            evaluate_formula(ast, {})
        assert exc.value.error_code == "PRICING_VALUE_NOT_DECIMAL"


class TestVar:
    def test_var_lookup(self) -> None:
        ast = _ast(_b("final_price", {"var": "cost"}, tag="final_price"))
        result = evaluate_formula(ast, {"cost": Decimal("12.34")})
        assert result.final_price == Decimal("12.34")

    def test_missing_variable(self) -> None:
        ast = _ast(_b("final_price", {"var": "cost"}, tag="final_price"))
        with pytest.raises(FormulaEvaluationError) as exc:
            evaluate_formula(ast, {})
        assert exc.value.error_code == "PRICING_VARIABLE_MISSING"
        assert exc.value.details["variable"] == "cost"


class TestRef:
    def test_ref_chain(self) -> None:
        ast = _ast(
            _b("base", {"const": "10"}),
            _b("doubled", {"op": "*", "args": [{"ref": "base"}, {"const": "2"}]}),
            _b(
                "final_price",
                {"op": "+", "args": [{"ref": "doubled"}, {"const": "5"}]},
                tag="final_price",
            ),
        )
        result = evaluate_formula(ast, {})
        assert result.final_price == Decimal("25")
        assert result.components == {
            "base": Decimal("10"),
            "doubled": Decimal("20"),
            "final_price": Decimal("25"),
        }


# ---------------------------------------------------------------------------
# Operators
# ---------------------------------------------------------------------------


class TestOperators:
    def test_add_nary(self) -> None:
        ast = _ast(
            _b(
                "final_price",
                {"op": "+", "args": [{"const": "1"}, {"const": "2"}, {"const": "3"}]},
                tag="final_price",
            )
        )
        assert evaluate_formula(ast, {}).final_price == Decimal("6")

    def test_multiply_nary(self) -> None:
        ast = _ast(
            _b(
                "final_price",
                {"op": "*", "args": [{"const": "2"}, {"const": "3"}, {"const": "4"}]},
                tag="final_price",
            )
        )
        assert evaluate_formula(ast, {}).final_price == Decimal("24")

    def test_subtract_binary(self) -> None:
        ast = _ast(
            _b(
                "final_price",
                {"op": "-", "args": [{"const": "10"}, {"const": "3"}]},
                tag="final_price",
            )
        )
        assert evaluate_formula(ast, {}).final_price == Decimal("7")

    def test_divide_binary(self) -> None:
        ast = _ast(
            _b(
                "final_price",
                {"op": "/", "args": [{"const": "10"}, {"const": "4"}]},
                tag="final_price",
            )
        )
        assert evaluate_formula(ast, {}).final_price == Decimal("2.5")

    def test_division_by_zero(self) -> None:
        ast = _ast(
            _b(
                "final_price",
                {"op": "/", "args": [{"const": "10"}, {"const": "0"}]},
                tag="final_price",
            )
        )
        with pytest.raises(FormulaEvaluationError) as exc:
            evaluate_formula(ast, {})
        assert exc.value.error_code == "PRICING_DIVISION_BY_ZERO"

    def test_add_arity_enforced(self) -> None:
        ast = _ast(
            _b("final_price", {"op": "+", "args": [{"const": "1"}]}, tag="final_price")
        )
        with pytest.raises(FormulaEvaluationError) as exc:
            evaluate_formula(ast, {})
        assert exc.value.error_code == "PRICING_FN_ARITY"

    def test_subtract_arity_enforced(self) -> None:
        ast = _ast(
            _b(
                "final_price",
                {"op": "-", "args": [{"const": "1"}, {"const": "2"}, {"const": "3"}]},
                tag="final_price",
            )
        )
        with pytest.raises(FormulaEvaluationError) as exc:
            evaluate_formula(ast, {})
        assert exc.value.error_code == "PRICING_FN_ARITY"

    def test_unknown_operator(self) -> None:
        ast = _ast(
            _b(
                "final_price",
                {"op": "%", "args": [{"const": "1"}, {"const": "2"}]},
                tag="final_price",
            )
        )
        with pytest.raises(FormulaEvaluationError) as exc:
            evaluate_formula(ast, {})
        assert exc.value.error_code == "PRICING_OP_UNKNOWN"


# ---------------------------------------------------------------------------
# Functions
# ---------------------------------------------------------------------------


class TestFunctions:
    def test_min_nary(self) -> None:
        ast = _ast(
            _b(
                "final_price",
                {
                    "fn": "min",
                    "args": [{"const": "5"}, {"const": "2"}, {"const": "8"}],
                },
                tag="final_price",
            )
        )
        assert evaluate_formula(ast, {}).final_price == Decimal("2")

    def test_max_nary(self) -> None:
        ast = _ast(
            _b(
                "final_price",
                {
                    "fn": "max",
                    "args": [{"const": "5"}, {"const": "2"}, {"const": "8"}],
                },
                tag="final_price",
            )
        )
        assert evaluate_formula(ast, {}).final_price == Decimal("8")

    def test_abs_negative(self) -> None:
        ast = _ast(
            _b(
                "final_price",
                {"fn": "abs", "args": [{"const": "-7.5"}]},
                tag="final_price",
            )
        )
        assert evaluate_formula(ast, {}).final_price == Decimal("7.5")

    def test_abs_arity(self) -> None:
        ast = _ast(
            _b(
                "final_price",
                {"fn": "abs", "args": [{"const": "1"}, {"const": "2"}]},
                tag="final_price",
            )
        )
        with pytest.raises(FormulaEvaluationError) as exc:
            evaluate_formula(ast, {})
        assert exc.value.error_code == "PRICING_FN_ARITY"

    def test_round_half_up(self) -> None:
        ast = _ast(
            _b(
                "final_price",
                {"fn": "round", "args": [{"const": "2.5"}]},
                tag="final_price",
            )
        )
        # HALF_UP (not banker's) → 3
        assert evaluate_formula(ast, {}).final_price == Decimal("3")

    def test_round_with_digits(self) -> None:
        ast = _ast(
            _b(
                "final_price",
                {"fn": "round", "args": [{"const": "2.345"}, {"const": "2"}]},
                tag="final_price",
            )
        )
        assert evaluate_formula(ast, {}).final_price == Decimal("2.35")

    def test_ceil(self) -> None:
        ast = _ast(
            _b(
                "final_price",
                {"fn": "ceil", "args": [{"const": "2.01"}]},
                tag="final_price",
            )
        )
        assert evaluate_formula(ast, {}).final_price == Decimal("3")

    def test_floor(self) -> None:
        ast = _ast(
            _b(
                "final_price",
                {"fn": "floor", "args": [{"const": "2.99"}]},
                tag="final_price",
            )
        )
        assert evaluate_formula(ast, {}).final_price == Decimal("2")

    def test_if_truthy(self) -> None:
        ast = _ast(
            _b(
                "final_price",
                {
                    "fn": "if",
                    "args": [{"const": "1"}, {"const": "100"}, {"const": "200"}],
                },
                tag="final_price",
            )
        )
        assert evaluate_formula(ast, {}).final_price == Decimal("100")

    def test_if_falsy(self) -> None:
        ast = _ast(
            _b(
                "final_price",
                {
                    "fn": "if",
                    "args": [{"const": "0"}, {"const": "100"}, {"const": "200"}],
                },
                tag="final_price",
            )
        )
        assert evaluate_formula(ast, {}).final_price == Decimal("200")

    def test_if_arity(self) -> None:
        ast = _ast(
            _b(
                "final_price",
                {"fn": "if", "args": [{"const": "1"}, {"const": "2"}]},
                tag="final_price",
            )
        )
        with pytest.raises(FormulaEvaluationError) as exc:
            evaluate_formula(ast, {})
        assert exc.value.error_code == "PRICING_FN_ARITY"

    def test_unknown_function(self) -> None:
        ast = _ast(
            _b(
                "final_price",
                {"fn": "sqrt", "args": [{"const": "4"}]},
                tag="final_price",
            )
        )
        with pytest.raises(FormulaEvaluationError) as exc:
            evaluate_formula(ast, {})
        assert exc.value.error_code == "PRICING_FN_UNKNOWN"


# ---------------------------------------------------------------------------
# Integration-style: realistic pricing formula
# ---------------------------------------------------------------------------


class TestRealisticFormula:
    def test_margin_plus_vat(self) -> None:
        # markup = cost * (1 + margin_pct)
        # with_vat = markup * (1 + vat_pct)
        # final_price = max(with_vat, min_price)
        ast = _ast(
            _b(
                "markup",
                {
                    "op": "*",
                    "args": [
                        {"var": "cost"},
                        {
                            "op": "+",
                            "args": [{"const": "1"}, {"var": "margin_pct"}],
                        },
                    ],
                },
            ),
            _b(
                "with_vat",
                {
                    "op": "*",
                    "args": [
                        {"ref": "markup"},
                        {"op": "+", "args": [{"const": "1"}, {"var": "vat_pct"}]},
                    ],
                },
            ),
            _b(
                "final_price",
                {
                    "fn": "max",
                    "args": [{"ref": "with_vat"}, {"var": "min_price"}],
                },
                tag="final_price",
            ),
        )
        variables = {
            "cost": Decimal("100"),
            "margin_pct": Decimal("0.20"),
            "vat_pct": Decimal("0.12"),
            "min_price": Decimal("50"),
        }
        result = evaluate_formula(ast, variables)
        # markup = 100 * 1.20 = 120
        # with_vat = 120 * 1.12 = 134.4
        # final_price = max(134.4, 50) = 134.4
        assert result.final_price == Decimal("134.40")
        assert result.components["markup"] == Decimal("120.00")
        assert result.components["with_vat"] == Decimal("134.4000")

    def test_decimal_precision_preserved(self) -> None:
        # No float leakage; 0.1 + 0.2 must equal exactly 0.3.
        ast = _ast(
            _b(
                "final_price",
                {"op": "+", "args": [{"const": "0.1"}, {"const": "0.2"}]},
                tag="final_price",
            )
        )
        assert evaluate_formula(ast, {}).final_price == Decimal("0.3")


# ---------------------------------------------------------------------------
# Structural defences
# ---------------------------------------------------------------------------


class TestStructuralDefences:
    def test_empty_bindings(self) -> None:
        with pytest.raises(FormulaEvaluationError):
            evaluate_formula({"version": 1, "bindings": []}, {})

    def test_missing_final_price(self) -> None:
        ast = _ast(_b("total", {"const": "1"}))
        with pytest.raises(FormulaEvaluationError):
            evaluate_formula(ast, {})

    def test_forward_ref_rejected(self) -> None:
        ast = _ast(
            _b("final_price", {"ref": "later"}, tag="final_price"),
            _b("later", {"const": "1"}),
        )
        with pytest.raises(FormulaEvaluationError) as exc:
            evaluate_formula(ast, {})
        assert exc.value.error_code == "PRICING_FORMULA_EVALUATION_FAILED"

    def test_non_dict_expr(self) -> None:
        ast = _ast({"name": "final_price", "component_tag": "final_price", "expr": 42})
        with pytest.raises(FormulaEvaluationError):
            evaluate_formula(ast, {})

    def test_unknown_node_shape(self) -> None:
        ast = _ast(
            _b("final_price", {"wat": "nope"}, tag="final_price"),
        )
        with pytest.raises(FormulaEvaluationError):
            evaluate_formula(ast, {})


class TestResultContract:
    def test_returns_evaluation_result(self) -> None:
        ast = _ast(_b("final_price", {"const": "1"}, tag="final_price"))
        result = evaluate_formula(ast, {})
        assert isinstance(result, EvaluationResult)
        assert result.components["final_price"] == result.final_price
