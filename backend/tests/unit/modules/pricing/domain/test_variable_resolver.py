"""Unit tests for pure-domain variable resolution."""

from __future__ import annotations

import uuid
from decimal import Decimal

import pytest

from src.modules.pricing.domain.category_pricing_settings import (
    CategoryPricingSettings,
)
from src.modules.pricing.domain.entities import ProductPricingProfile
from src.modules.pricing.domain.exceptions import FormulaEvaluationError
from src.modules.pricing.domain.supplier_pricing_settings import (
    SupplierPricingSettings,
)
from src.modules.pricing.domain.value_objects import VariableDataType, VariableScope
from src.modules.pricing.domain.variable import Variable
from src.modules.pricing.domain.variable_resolver import resolve_variables

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _var(
    code: str,
    scope: VariableScope,
    *,
    is_required: bool = False,
    default: Decimal | None = None,
) -> Variable:
    return Variable.create(
        code=code,
        scope=scope,
        data_type=VariableDataType.DECIMAL,
        unit="RUB",
        name={"ru": code, "en": code},
        is_required=is_required,
        default_value=default,
        actor_id=uuid.uuid4(),
    )


def _profile(values: dict[str, Decimal]) -> ProductPricingProfile:
    return ProductPricingProfile.create(
        product_id=uuid.uuid4(),
        values=values,
        actor_id=uuid.uuid4(),
    )


def _settings(values: dict[str, Decimal]) -> CategoryPricingSettings:
    return CategoryPricingSettings.create(
        category_id=uuid.uuid4(),
        context_id=uuid.uuid4(),
        values=values,
        ranges=[],
        explicit_no_ranges=True,
        actor_id=uuid.uuid4(),
    )


def _supplier_settings(values: dict[str, Decimal]) -> SupplierPricingSettings:
    return SupplierPricingSettings.create(
        supplier_id=uuid.uuid4(),
        values=values,
        actor_id=uuid.uuid4(),
    )


# ---------------------------------------------------------------------------
# GLOBAL scope
# ---------------------------------------------------------------------------


class TestGlobalScope:
    def test_uses_default_value(self) -> None:
        v = _var("fx_usd", VariableScope.GLOBAL, default=Decimal("92.5"))
        resolved = resolve_variables([v])
        assert resolved == {"fx_usd": Decimal("92.5")}

    def test_no_default_optional_omitted(self) -> None:
        v = _var("fx_eur", VariableScope.GLOBAL)
        assert resolve_variables([v]) == {}

    def test_no_default_required_raises(self) -> None:
        v = _var("vat_pct", VariableScope.GLOBAL, is_required=True)
        with pytest.raises(FormulaEvaluationError) as exc:
            resolve_variables([v])
        assert exc.value.error_code == "PRICING_VARIABLE_MISSING"
        assert exc.value.details["variable"] == "vat_pct"
        assert exc.value.details["scope"] == "global"

    def test_product_profile_does_not_override_global(self) -> None:
        v = _var("fx_usd", VariableScope.GLOBAL, default=Decimal("92.5"))
        profile = _profile({"fx_usd": Decimal("9999")})
        resolved = resolve_variables([v], product_profile=profile)
        assert resolved == {"fx_usd": Decimal("92.5")}


# ---------------------------------------------------------------------------
# PRODUCT_INPUT scope
# ---------------------------------------------------------------------------


class TestProductInputScope:
    def test_profile_value_wins(self) -> None:
        v = _var(
            "purchase_price",
            VariableScope.PRODUCT_INPUT,
            default=Decimal("100"),
        )
        profile = _profile({"purchase_price": Decimal("250")})
        assert resolve_variables([v], product_profile=profile) == {
            "purchase_price": Decimal("250"),
        }

    def test_falls_back_to_default(self) -> None:
        v = _var(
            "purchase_price",
            VariableScope.PRODUCT_INPUT,
            default=Decimal("100"),
        )
        profile = _profile({})
        assert resolve_variables([v], product_profile=profile) == {
            "purchase_price": Decimal("100"),
        }

    def test_no_profile_no_default_required_raises(self) -> None:
        v = _var(
            "purchase_price",
            VariableScope.PRODUCT_INPUT,
            is_required=True,
        )
        with pytest.raises(FormulaEvaluationError) as exc:
            resolve_variables([v])
        assert exc.value.error_code == "PRICING_VARIABLE_MISSING"

    def test_no_profile_no_default_optional_omitted(self) -> None:
        v = _var("weight", VariableScope.PRODUCT_INPUT)
        assert resolve_variables([v]) == {}


# ---------------------------------------------------------------------------
# CATEGORY scope
# ---------------------------------------------------------------------------


class TestCategoryScope:
    def test_settings_value_wins(self) -> None:
        v = _var(
            "margin_pct",
            VariableScope.CATEGORY,
            default=Decimal("0.20"),
        )
        settings = _settings({"margin_pct": Decimal("0.35")})
        assert resolve_variables([v], category_settings=settings) == {
            "margin_pct": Decimal("0.35"),
        }

    def test_falls_back_to_default(self) -> None:
        v = _var(
            "margin_pct",
            VariableScope.CATEGORY,
            default=Decimal("0.20"),
        )
        settings = _settings({})
        assert resolve_variables([v], category_settings=settings) == {
            "margin_pct": Decimal("0.20"),
        }

    def test_no_settings_no_default_required_raises(self) -> None:
        v = _var("margin_pct", VariableScope.CATEGORY, is_required=True)
        with pytest.raises(FormulaEvaluationError) as exc:
            resolve_variables([v])
        assert exc.value.error_code == "PRICING_VARIABLE_MISSING"


# ---------------------------------------------------------------------------
# SUPPLIER scope
# ---------------------------------------------------------------------------


class TestSupplierScope:
    def test_supplier_value_wins_over_default(self) -> None:
        v = _var(
            "supplier_markup", VariableScope.SUPPLIER, default=Decimal("0.10")
        )
        settings = _supplier_settings({"supplier_markup": Decimal("0.25")})
        assert resolve_variables([v], supplier_settings=settings) == {
            "supplier_markup": Decimal("0.25")
        }

    def test_supplier_falls_back_to_default_when_missing(self) -> None:
        v = _var(
            "supplier_markup", VariableScope.SUPPLIER, default=Decimal("0.10")
        )
        settings = _supplier_settings({"other": Decimal("1")})
        assert resolve_variables([v], supplier_settings=settings) == {
            "supplier_markup": Decimal("0.10")
        }

    def test_supplier_no_settings_uses_default(self) -> None:
        v = _var(
            "supplier_markup", VariableScope.SUPPLIER, default=Decimal("0.10")
        )
        assert resolve_variables([v]) == {"supplier_markup": Decimal("0.10")}

    def test_supplier_required_no_value_no_default_raises(self) -> None:
        v = _var("supplier_markup", VariableScope.SUPPLIER, is_required=True)
        with pytest.raises(FormulaEvaluationError) as exc:
            resolve_variables([v])
        assert exc.value.error_code == "PRICING_VARIABLE_MISSING"


# ---------------------------------------------------------------------------
# RANGE scope — deferred
# ---------------------------------------------------------------------------


class TestDeferredScopes:
    def test_range_uses_default_only(self) -> None:
        v = _var("bucket_markup", VariableScope.RANGE, default=Decimal("5"))
        assert resolve_variables([v]) == {"bucket_markup": Decimal("5")}


# ---------------------------------------------------------------------------
# Integration — multi-variable resolution
# ---------------------------------------------------------------------------


class TestIntegration:
    def test_mixed_scopes(self) -> None:
        variables = [
            _var("fx_usd", VariableScope.GLOBAL, default=Decimal("92.5")),
            _var(
                "purchase_price",
                VariableScope.PRODUCT_INPUT,
                is_required=True,
            ),
            _var("margin_pct", VariableScope.CATEGORY, default=Decimal("0.20")),
        ]
        profile = _profile({"purchase_price": Decimal("100")})
        settings = _settings({"margin_pct": Decimal("0.35")})

        resolved = resolve_variables(
            variables,
            product_profile=profile,
            category_settings=settings,
        )
        assert resolved == {
            "fx_usd": Decimal("92.5"),
            "purchase_price": Decimal("100"),
            "margin_pct": Decimal("0.35"),
        }

    def test_empty_registry(self) -> None:
        assert resolve_variables([]) == {}

    def test_missing_required_reports_first_failure(self) -> None:
        variables = [
            _var("fx_usd", VariableScope.GLOBAL, default=Decimal("92.5")),
            _var("vat_pct", VariableScope.GLOBAL, is_required=True),
        ]
        with pytest.raises(FormulaEvaluationError) as exc:
            resolve_variables(variables)
        assert exc.value.details["variable"] == "vat_pct"

    def test_extra_profile_values_ignored_when_not_in_registry(self) -> None:
        # Profile has a code that isn't in the registry → silently skipped.
        v = _var("cost", VariableScope.PRODUCT_INPUT, default=Decimal("1"))
        profile = _profile({"cost": Decimal("10"), "ghost": Decimal("999")})
        resolved = resolve_variables([v], product_profile=profile)
        assert resolved == {"cost": Decimal("10")}
