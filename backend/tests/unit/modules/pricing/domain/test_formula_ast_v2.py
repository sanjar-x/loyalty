"""Unit tests for the v2 AST contract (T-X / Sprint 4).

Covers:

* :func:`normalize_ast_to_v2` — lifts v1 (``name`` + ``component_tag``)
  into v2 (``code`` + ``label_i18n`` + ``is_visible``) with deterministic
  defaults, idempotent on already-v2 input.
* :func:`_validate_ast` — strict v2 contract (label_i18n required,
  final_component_code mandatory, unique codes).
* :func:`evaluate_formula` — reads ``final_component_code`` from the
  AST root and handles both v1 and v2 keys via ``_binding_code``.
* :func:`_build_breakdown` — projects evaluator output through AST
  metadata into the labelled list the admin UI consumes.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from src.modules.pricing.application.queries.preview_sku_pricing import (
    ComponentBreakdown,
    _build_breakdown,
)
from src.modules.pricing.domain.entities.formula import (
    _validate_ast,
    normalize_ast_to_v2,
)
from src.modules.pricing.domain.exceptions import FormulaValidationError
from src.modules.pricing.domain.formula_evaluator import evaluate_formula

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# normalize_ast_to_v2
# ---------------------------------------------------------------------------


class TestNormalizeAstToV2:
    def test_v1_ast_gets_code_label_visibility_and_final_pointer(self) -> None:
        v1 = {
            "version": 1,
            "bindings": [
                {
                    "name": "tsena_v_rublyakh",
                    "component_tag": "tsena_v_rublyakh",
                    "expr": {"const": "100"},
                },
                {
                    "name": "final_price",
                    "component_tag": "final_price",
                    "expr": {"ref": "tsena_v_rublyakh"},
                },
            ],
        }
        v2 = normalize_ast_to_v2(v1)
        assert v2["final_component_code"] == "final_price"
        first = v2["bindings"][0]
        assert first["code"] == "tsena_v_rublyakh"
        assert first["label_i18n"] == {"ru": "Tsena v rublyakh"}
        assert first["is_visible"] is True
        # Original v1 fields are preserved for backward compatibility
        # with any consumer that still reads ``name`` / ``component_tag``.
        assert first["name"] == "tsena_v_rublyakh"

    def test_component_tag_wins_over_name_when_both_present(self) -> None:
        v1 = {
            "version": 1,
            "bindings": [
                {
                    "name": "internal",
                    "component_tag": "tsena_v_rublyakh",
                    "expr": {"const": "1"},
                },
                {
                    "name": "final_price",
                    "component_tag": "final_price",
                    "expr": {"const": "100"},
                },
            ],
        }
        v2 = normalize_ast_to_v2(v1)
        assert v2["bindings"][0]["code"] == "tsena_v_rublyakh"

    def test_idempotent_on_already_v2(self) -> None:
        v2 = {
            "version": 1,
            "final_component_code": "final_price",
            "bindings": [
                {
                    "code": "final_price",
                    "label_i18n": {"ru": "Итоговая цена"},
                    "is_visible": True,
                    "expr": {"const": "10"},
                }
            ],
        }
        result = normalize_ast_to_v2(v2)
        assert result == v2

    def test_existing_label_is_preserved(self) -> None:
        partial = {
            "version": 1,
            "bindings": [
                {
                    "name": "final_price",
                    "component_tag": "final_price",
                    "label_i18n": {"ru": "Цена"},
                    "expr": {"const": "10"},
                }
            ],
        }
        v2 = normalize_ast_to_v2(partial)
        assert v2["bindings"][0]["label_i18n"] == {"ru": "Цена"}

    def test_falls_back_to_last_binding_when_no_final_price_named(self) -> None:
        v1 = {
            "version": 1,
            "bindings": [
                {
                    "name": "tail",
                    "component_tag": "tail",
                    "expr": {"const": "1"},
                }
            ],
        }
        v2 = normalize_ast_to_v2(v1)
        assert v2["final_component_code"] == "tail"


# ---------------------------------------------------------------------------
# _validate_ast (v2 contract)
# ---------------------------------------------------------------------------


def _v2_minimal_ast(*, label_i18n: dict[str, str] | None = None) -> dict:
    return {
        "version": 1,
        "final_component_code": "final_price",
        "bindings": [
            {
                "code": "final_price",
                "label_i18n": label_i18n or {"ru": "Итоговая цена"},
                "is_visible": True,
                "expr": {"const": "100"},
            }
        ],
    }


class TestValidateAstV2:
    def test_happy_path(self) -> None:
        _validate_ast(_v2_minimal_ast())

    def test_rejects_missing_final_component_code(self) -> None:
        ast = _v2_minimal_ast()
        del ast["final_component_code"]
        with pytest.raises(FormulaValidationError) as exc:
            _validate_ast(ast)
        assert exc.value.error_code == "PRICING_FORMULA_FINAL_COMPONENT_MISSING"

    def test_rejects_unresolved_final_component_code(self) -> None:
        ast = _v2_minimal_ast()
        ast["final_component_code"] = "does_not_exist"
        with pytest.raises(FormulaValidationError) as exc:
            _validate_ast(ast)
        assert exc.value.error_code == "PRICING_FORMULA_FINAL_COMPONENT_UNRESOLVED"

    def test_rejects_missing_label_i18n(self) -> None:
        ast = _v2_minimal_ast()
        del ast["bindings"][0]["label_i18n"]
        with pytest.raises(FormulaValidationError) as exc:
            _validate_ast(ast)
        assert exc.value.error_code == "PRICING_FORMULA_LABEL_I18N_MISSING"

    def test_rejects_label_i18n_without_required_ru_locale(self) -> None:
        ast = _v2_minimal_ast(label_i18n={"en": "Final price"})
        with pytest.raises(FormulaValidationError) as exc:
            _validate_ast(ast)
        assert exc.value.error_code == "PRICING_FORMULA_LABEL_I18N_INCOMPLETE"
        assert exc.value.details["missing"] == ["ru"]

    def test_rejects_blank_label_i18n_value(self) -> None:
        ast = _v2_minimal_ast(label_i18n={"ru": "   "})
        with pytest.raises(FormulaValidationError) as exc:
            _validate_ast(ast)
        assert exc.value.error_code == "PRICING_FORMULA_LABEL_I18N_INVALID"

    def test_rejects_non_boolean_is_visible(self) -> None:
        ast = _v2_minimal_ast()
        ast["bindings"][0]["is_visible"] = "yes"
        with pytest.raises(FormulaValidationError) as exc:
            _validate_ast(ast)
        assert exc.value.error_code == "PRICING_FORMULA_AST_VISIBILITY_INVALID"


# ---------------------------------------------------------------------------
# evaluate_formula — final_component_code routing
# ---------------------------------------------------------------------------


class TestEvaluatorFinalComponentCode:
    def test_reads_explicit_final_component_code(self) -> None:
        ast = {
            "version": 1,
            "final_component_code": "selling_price",
            "bindings": [
                {
                    "code": "selling_price",
                    "label_i18n": {"ru": "Продажная цена"},
                    "is_visible": True,
                    "expr": {"const": "42.5"},
                }
            ],
        }
        result = evaluate_formula(ast, {})
        assert result.final_price == Decimal("42.5")
        assert result.components == {"selling_price": Decimal("42.5")}

    def test_falls_back_to_final_price_when_pointer_missing(self) -> None:
        """v1 AST that bypassed migration still evaluates correctly."""
        ast = {
            "version": 1,
            "bindings": [
                {
                    "name": "final_price",
                    "component_tag": "final_price",
                    "expr": {"const": "7"},
                }
            ],
        }
        result = evaluate_formula(ast, {})
        assert result.final_price == Decimal("7")


# ---------------------------------------------------------------------------
# _build_breakdown
# ---------------------------------------------------------------------------


class TestBuildBreakdown:
    def test_uses_label_i18n_directly(self) -> None:
        ast = {
            "version": 1,
            "final_component_code": "final_price",
            "bindings": [
                {
                    "code": "tsena_v_rublyakh",
                    "label_i18n": {"ru": "Цена в рублях"},
                    "is_visible": True,
                    "expr": {"const": "100"},
                },
                {
                    "code": "final_price",
                    "label_i18n": {"ru": "Итоговая цена"},
                    "is_visible": True,
                    "expr": {"const": "115"},
                },
            ],
        }
        components = {
            "tsena_v_rublyakh": Decimal("100"),
            "final_price": Decimal("115"),
        }
        breakdown = _build_breakdown(ast=ast, components=components)
        assert breakdown == [
            ComponentBreakdown(
                code="tsena_v_rublyakh",
                name="Цена в рублях",
                value=Decimal("100"),
                is_visible=True,
                is_final=False,
            ),
            ComponentBreakdown(
                code="final_price",
                name="Итоговая цена",
                value=Decimal("115"),
                is_visible=True,
                is_final=True,
            ),
        ]

    def test_respects_is_visible_false(self) -> None:
        ast = {
            "version": 1,
            "final_component_code": "final_price",
            "bindings": [
                {
                    "code": "internal_step",
                    "label_i18n": {"ru": "Промежуточный шаг"},
                    "is_visible": False,
                    "expr": {"const": "10"},
                },
                {
                    "code": "final_price",
                    "label_i18n": {"ru": "Итоговая цена"},
                    "is_visible": True,
                    "expr": {"const": "20"},
                },
            ],
        }
        breakdown = _build_breakdown(
            ast=ast,
            components={
                "internal_step": Decimal("10"),
                "final_price": Decimal("20"),
            },
        )
        # Row is still surfaced — the UI is responsible for filtering;
        # backend just hands the flag along.
        assert breakdown[0].is_visible is False
        assert breakdown[1].is_visible is True

    def test_falls_back_to_humanized_for_missing_label(self) -> None:
        """Defensive: AST bypassed normalisation, breakdown still renders."""
        ast = {
            "version": 1,
            "final_component_code": "final_price",
            "bindings": [
                {
                    "code": "tsena_s_dostavkoy",
                    "expr": {"const": "1"},
                },
                {
                    "code": "final_price",
                    "label_i18n": {"ru": "Итоговая цена"},
                    "is_visible": True,
                    "expr": {"const": "2"},
                },
            ],
        }
        breakdown = _build_breakdown(
            ast=ast,
            components={
                "tsena_s_dostavkoy": Decimal("1"),
                "final_price": Decimal("2"),
            },
        )
        assert breakdown[0].name == "Tsena s dostavkoy"
