"""Unit tests for the pure-domain SKU pricing recompute (ADR-005).

Verifies idempotency, FX-staleness gating, missing-input handling, and
deterministic ``inputs_hash`` semantics that the autonomous recompute
pipeline relies on for at-least-once → exactly-once-effective delivery.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from src.modules.pricing.domain.entities.variable import Variable
from src.modules.pricing.domain.interfaces import (
    SkuPricingInputs,
    SkuPricingScopeSnapshot,
)
from src.modules.pricing.domain.recompute import (
    SkuPricingComputed,
    SkuPricingFailed,
    recompute_sku_pricing,
)
from src.modules.pricing.domain.value_objects import (
    RoundingMode,
    VariableDataType,
    VariableScope,
)

_ACTOR = uuid.uuid4()


def _var(
    code: str,
    *,
    scope: VariableScope,
    is_required: bool = False,
    is_fx_rate: bool = False,
    max_age_days: int | None = None,
    default_value: Decimal | None = None,
    unit: str = "RUB",
) -> Variable:
    return Variable.create(
        code=code,
        scope=scope,
        data_type=VariableDataType.DECIMAL,
        unit=unit,
        name={"ru": code, "en": code},
        is_required=is_required,
        default_value=default_value,
        is_fx_rate=is_fx_rate,
        max_age_days=max_age_days,
        actor_id=_ACTOR,
    )


def _basic_inputs(
    *,
    purchase_price: Decimal | None = Decimal("100.00"),
    purchase_currency: str | None = "RUB",
    pricing_status: str = "pending",
) -> SkuPricingInputs:
    return SkuPricingInputs(
        sku_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        product_id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
        variant_id=uuid.UUID("33333333-3333-3333-3333-333333333333"),
        category_id=uuid.UUID("44444444-4444-4444-4444-444444444444"),
        supplier_id=uuid.UUID("55555555-5555-5555-5555-555555555555"),
        supplier_type="LOCAL",
        purchase_price=purchase_price,
        purchase_currency=purchase_currency,
        version=1,
        pricing_status=pricing_status,
    )


def _scope_with_simple_markup(
    *,
    variables: tuple[Variable, ...] | None = None,
    global_values: dict[str, Decimal] | None = None,
    global_value_set_at: dict[str, datetime] | None = None,
    formula_ast: dict | None = None,
    rounding_step: Decimal | None = Decimal("0.01"),
) -> SkuPricingScopeSnapshot:
    vars_ = (
        variables
        if variables is not None
        else (
            _var("purchase_price_rub", scope=VariableScope.SKU_INPUT, unit="RUB"),
            _var("supplier_margin_pct", scope=VariableScope.SUPPLIER, unit="PCT"),
        )
    )
    return SkuPricingScopeSnapshot(
        context_id=uuid.UUID("66666666-6666-6666-6666-666666666666"),
        target_currency="RUB",
        rounding_mode=RoundingMode.HALF_UP.value,
        rounding_step=rounding_step,
        formula_version_id=uuid.UUID("77777777-7777-7777-7777-777777777777"),
        formula_version_number=1,
        formula_ast=formula_ast or _markup_ast(),
        evaluation_timeout_ms=1000,
        variables=vars_,
        global_values=global_values or {},
        global_value_set_at=global_value_set_at or {},
        category_values={},
        supplier_values={"supplier_margin_pct": Decimal("20")},
        settings_versions=(("supplier", 3),),
    )


def _markup_ast() -> dict:
    """``final_price = purchase_price_rub * (1 + supplier_margin_pct / 100)``."""
    return {
        "bindings": [
            {
                "name": "final_price",
                "expr": {
                    "op": "*",
                    "args": [
                        {"var": "purchase_price_rub"},
                        {
                            "op": "+",
                            "args": [
                                {"const": "1"},
                                {
                                    "op": "/",
                                    "args": [
                                        {"var": "supplier_margin_pct"},
                                        {"const": "100"},
                                    ],
                                },
                            ],
                        },
                    ],
                },
            },
        ],
    }


def _cny_to_rub_ast() -> dict:
    """Single-currency CNY context: ``final_price = purchase_price_cny * fx_cny_rub``.

    ADR-005 requires single-currency formulas — the inactive-currency
    SKU_INPUT variable stays absent from the resolved map, so an
    eager-evaluated ``if(..., else: purchase_price_rub)`` against a
    CNY SKU would deliberately raise ``PRICING_VARIABLE_MISSING``.
    Multi-currency catalogs route SKUs to the right context via the
    supplier_type→context mapping rather than branching inside a
    single formula.
    """
    return {
        "bindings": [
            {
                "name": "final_price",
                "expr": {
                    "op": "*",
                    "args": [
                        {"var": "purchase_price_cny"},
                        {"var": "fx_cny_rub"},
                    ],
                },
            },
        ],
    }


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


class TestRecomputeHappyPath:
    def test_simple_markup(self):
        result = recompute_sku_pricing(_basic_inputs(), _scope_with_simple_markup())
        assert isinstance(result, SkuPricingComputed)
        # 100 * (1 + 20/100) = 120.00
        assert result.selling_price == Decimal("120.00")
        assert result.selling_currency == "RUB"
        assert result.formula_version_id is not None
        assert len(result.inputs_hash) == 64

    def test_cny_to_rub_via_fx(self):
        variables = (
            _var("purchase_price_rub", scope=VariableScope.SKU_INPUT, unit="RUB"),
            _var("purchase_price_cny", scope=VariableScope.SKU_INPUT, unit="CNY"),
            _var(
                "fx_cny_rub",
                scope=VariableScope.GLOBAL,
                is_fx_rate=True,
                max_age_days=14,
                unit="RUB",
            ),
        )
        scope = SkuPricingScopeSnapshot(
            context_id=uuid.uuid4(),
            target_currency="RUB",
            rounding_mode=RoundingMode.HALF_UP.value,
            rounding_step=Decimal("0.01"),
            formula_version_id=uuid.uuid4(),
            formula_version_number=1,
            formula_ast=_cny_to_rub_ast(),
            evaluation_timeout_ms=1000,
            variables=variables,
            global_values={"fx_cny_rub": Decimal("12.5")},
            global_value_set_at={"fx_cny_rub": datetime.now(UTC)},
            category_values={},
            supplier_values={},
            settings_versions=(),
        )
        inputs = _basic_inputs(
            purchase_price=Decimal("50.00"),
            purchase_currency="CNY",
        )
        result = recompute_sku_pricing(inputs, scope)
        assert isinstance(result, SkuPricingComputed)
        # 50 * 12.5 = 625.00
        assert result.selling_price == Decimal("625.00")


# ---------------------------------------------------------------------------
# Idempotency — inputs_hash is deterministic and changes on real changes
# ---------------------------------------------------------------------------


class TestInputsHashDeterminism:
    def test_identical_inputs_yield_identical_hash(self):
        a = recompute_sku_pricing(_basic_inputs(), _scope_with_simple_markup())
        b = recompute_sku_pricing(_basic_inputs(), _scope_with_simple_markup())
        assert isinstance(a, SkuPricingComputed)
        assert isinstance(b, SkuPricingComputed)
        assert a.inputs_hash == b.inputs_hash

    def test_purchase_price_change_changes_hash(self):
        a = recompute_sku_pricing(
            _basic_inputs(purchase_price=Decimal("100.00")),
            _scope_with_simple_markup(),
        )
        b = recompute_sku_pricing(
            _basic_inputs(purchase_price=Decimal("101.00")),
            _scope_with_simple_markup(),
        )
        assert isinstance(a, SkuPricingComputed)
        assert isinstance(b, SkuPricingComputed)
        assert a.inputs_hash != b.inputs_hash

    def test_supplier_settings_version_change_changes_hash(self):
        scope_v3 = _scope_with_simple_markup()
        scope_v4 = SkuPricingScopeSnapshot(
            **{
                **scope_v3.__dict__,
                "settings_versions": (("supplier", 4),),
            }  # ty: ignore[invalid-argument-type]
        )
        a = recompute_sku_pricing(_basic_inputs(), scope_v3)
        b = recompute_sku_pricing(_basic_inputs(), scope_v4)
        assert isinstance(a, SkuPricingComputed)
        assert isinstance(b, SkuPricingComputed)
        assert a.inputs_hash != b.inputs_hash


# ---------------------------------------------------------------------------
# Failure modes
# ---------------------------------------------------------------------------


class TestRecomputeFailures:
    def test_missing_purchase_price(self):
        result = recompute_sku_pricing(
            _basic_inputs(purchase_price=None, purchase_currency=None),
            _scope_with_simple_markup(),
        )
        assert isinstance(result, SkuPricingFailed)
        assert result.status == "missing_purchase_price"

    def test_stale_fx_rate(self):
        variables = (
            _var("purchase_price_cny", scope=VariableScope.SKU_INPUT, unit="CNY"),
            _var("purchase_price_rub", scope=VariableScope.SKU_INPUT, unit="RUB"),
            _var(
                "fx_cny_rub",
                scope=VariableScope.GLOBAL,
                is_fx_rate=True,
                max_age_days=14,
                unit="RUB",
            ),
        )
        old = datetime.now(UTC) - timedelta(days=20)
        scope = SkuPricingScopeSnapshot(
            context_id=uuid.uuid4(),
            target_currency="RUB",
            rounding_mode=RoundingMode.HALF_UP.value,
            rounding_step=Decimal("0.01"),
            formula_version_id=uuid.uuid4(),
            formula_version_number=1,
            formula_ast=_cny_to_rub_ast(),
            evaluation_timeout_ms=1000,
            variables=variables,
            global_values={"fx_cny_rub": Decimal("12.5")},
            global_value_set_at={"fx_cny_rub": old},
            category_values={},
            supplier_values={},
            settings_versions=(),
        )
        inputs = _basic_inputs(
            purchase_price=Decimal("50.00"),
            purchase_currency="CNY",
        )
        result = recompute_sku_pricing(inputs, scope)
        assert isinstance(result, SkuPricingFailed)
        assert result.status == "stale_fx"
        assert "fx_cny_rub" in result.reason

    def test_fx_unconfigured_when_required(self):
        variables = (
            _var("purchase_price_cny", scope=VariableScope.SKU_INPUT, unit="CNY"),
            _var("purchase_price_rub", scope=VariableScope.SKU_INPUT, unit="RUB"),
            _var(
                "fx_cny_rub",
                scope=VariableScope.GLOBAL,
                is_fx_rate=True,
                max_age_days=14,
                unit="RUB",
            ),
        )
        scope = SkuPricingScopeSnapshot(
            context_id=uuid.uuid4(),
            target_currency="RUB",
            rounding_mode=RoundingMode.HALF_UP.value,
            rounding_step=Decimal("0.01"),
            formula_version_id=uuid.uuid4(),
            formula_version_number=1,
            formula_ast=_cny_to_rub_ast(),
            evaluation_timeout_ms=1000,
            variables=variables,
            global_values={},  # fx_cny_rub never set
            global_value_set_at={},
            category_values={},
            supplier_values={},
            settings_versions=(),
        )
        inputs = _basic_inputs(
            purchase_price=Decimal("50.00"),
            purchase_currency="CNY",
        )
        result = recompute_sku_pricing(inputs, scope)
        assert isinstance(result, SkuPricingFailed)
        assert result.status == "stale_fx"
        assert "not configured" in result.reason

    def test_unsupported_purchase_currency_raises(self):
        # Only RUB / CNY supported; anything else is a wiring bug.
        from src.modules.pricing.domain.exceptions import FormulaEvaluationError

        bad = SkuPricingInputs(
            sku_id=uuid.uuid4(),
            product_id=uuid.uuid4(),
            variant_id=uuid.uuid4(),
            category_id=uuid.uuid4(),
            supplier_id=None,
            supplier_type=None,
            purchase_price=Decimal("10.00"),
            purchase_currency="USD",
            version=1,
            pricing_status="pending",
        )
        with pytest.raises(FormulaEvaluationError):
            recompute_sku_pricing(bad, _scope_with_simple_markup())


# ---------------------------------------------------------------------------
# Rounding
# ---------------------------------------------------------------------------


class TestRounding:
    def test_default_quantum_is_two_decimal_places(self):
        # 99.999 with HALF_UP at 0.01 → 100.00
        ast = {
            "bindings": [
                {"name": "final_price", "expr": {"const": "99.999"}},
            ],
        }
        scope = _scope_with_simple_markup(
            formula_ast=ast,
            rounding_step=Decimal("0.01"),
        )
        result = recompute_sku_pricing(_basic_inputs(), scope)
        assert isinstance(result, SkuPricingComputed)
        assert result.selling_price == Decimal("100.00")

    def test_rounding_step_one(self):
        # 99.4 with HALF_UP at 1 → 99
        ast = {
            "bindings": [
                {"name": "final_price", "expr": {"const": "99.4"}},
            ],
        }
        scope = _scope_with_simple_markup(
            formula_ast=ast,
            rounding_step=Decimal("1"),
        )
        result = recompute_sku_pricing(_basic_inputs(), scope)
        assert isinstance(result, SkuPricingComputed)
        assert result.selling_price == Decimal("99")
