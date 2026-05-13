"""Unit tests for :class:`RecomputeSkuPricingService`.

The service stitches the pure-domain :func:`recompute_sku_pricing` to the
async catalog-apply port via ``loop.run_in_executor``. The pure domain
function is well-covered by ``tests/unit/modules/pricing/domain/test_recompute.py``,
but the **executor-wrapping wiring** has been historically untested —
which is how CAT-011 ("``recompute_sku_pricing() takes 2 positional
arguments but 3 were given``") shipped. Every recompute attempt died in
production.

This module locks the wiring in place: a regression of the wrapping
back to positional ``run_in_executor(None, fn, *args)`` would
immediately fail :class:`TestRecomputeServiceExecutorWiring`.
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any

import pytest
import structlog

from src.modules.catalog.domain.interfaces import (
    IInternalSkuPricingApplyPort,
    SkuPricingApplyRequest,
    SkuPricingFailureRequest,
    WriteOutcome,
)
from src.modules.pricing.domain.entities.variable import Variable
from src.modules.pricing.domain.interfaces import (
    ISkuPricingInputReader,
    ISkuPricingScopeReader,
    SkuPricingInputs,
    SkuPricingScopeSnapshot,
)
from src.modules.pricing.domain.value_objects import VariableDataType, VariableScope
from src.modules.pricing.infrastructure.services.recompute_service import (
    RecomputeSkuPricingService,
)

# ---------------------------------------------------------------------------
# Stub ports — return canned snapshots so we exercise just the wiring.
# ---------------------------------------------------------------------------


class _StubInputReader(ISkuPricingInputReader):
    def __init__(self, inputs: SkuPricingInputs | None) -> None:
        self._inputs = inputs

    async def read_one(
        self, sku_id: uuid.UUID, *, lock: bool = False
    ) -> SkuPricingInputs | None:
        return self._inputs

    # Bulk-iteration ports — unused by ``recompute_one`` but required by
    # the abstract base. Empty async generators keep the stub valid.
    async def iter_by_category(self, *a: Any, **k: Any) -> Any:
        return
        yield  # pragma: no cover — generator marker

    async def iter_by_supplier(self, *a: Any, **k: Any) -> Any:
        return
        yield  # pragma: no cover

    async def iter_by_context(self, *a: Any, **k: Any) -> Any:
        return
        yield  # pragma: no cover


class _StubScopeReader(ISkuPricingScopeReader):
    def __init__(self, scope: SkuPricingScopeSnapshot | None) -> None:
        self._scope = scope

    async def snapshot_for_sku(
        self, inputs: SkuPricingInputs
    ) -> SkuPricingScopeSnapshot | None:
        return self._scope


class _SpyApplyPort(IInternalSkuPricingApplyPort):
    """Captures every call so the test can assert what landed."""

    def __init__(
        self,
        success_outcome: WriteOutcome = WriteOutcome.APPLIED,
        failure_outcome: WriteOutcome = WriteOutcome.FAILURE_PERSISTED,
    ) -> None:
        self.success_calls: list[SkuPricingApplyRequest] = []
        self.failure_calls: list[SkuPricingFailureRequest] = []
        self._success_outcome = success_outcome
        self._failure_outcome = failure_outcome

    async def apply_success(self, request: SkuPricingApplyRequest) -> WriteOutcome:
        self.success_calls.append(request)
        return self._success_outcome

    async def apply_failure(self, request: SkuPricingFailureRequest) -> WriteOutcome:
        self.failure_calls.append(request)
        return self._failure_outcome


# ---------------------------------------------------------------------------
# Fixtures — build minimal SkuPricingInputs / Scope so the pure
# evaluator path actually runs.
# ---------------------------------------------------------------------------


def _build_variable(
    code: str, scope: VariableScope, *, default: Decimal | None = None
) -> Variable:
    return Variable.create(
        code=code,
        scope=scope,
        data_type=VariableDataType.DECIMAL,
        unit="RUB",
        name={"ru": code, "en": code},
        is_required=False,
        default_value=default,
        actor_id=uuid.uuid4(),
    )


def _build_inputs(*, version: int = 1) -> SkuPricingInputs:
    return SkuPricingInputs(
        sku_id=uuid.uuid4(),
        product_id=uuid.uuid4(),
        variant_id=uuid.uuid4(),
        category_id=uuid.uuid4(),
        supplier_id=None,
        supplier_type=None,
        purchase_price=Decimal("100"),
        purchase_currency="RUB",
        version=version,
        pricing_status="pending",
    )


def _build_scope(formula_id: uuid.UUID) -> SkuPricingScopeSnapshot:
    """Identity formula on ``purchase_price_rub`` — selling = purchase."""
    ast: dict[str, Any] = {
        "version": 1,
        "bindings": [
            {
                "name": "final_price",
                "component_tag": "final_price",
                "expr": {"var": "purchase_price_rub"},
            }
        ],
    }
    return SkuPricingScopeSnapshot(
        context_id=uuid.uuid4(),
        target_currency="RUB",
        target_currency_minor_unit=2,
        rounding_mode="HALF_UP",
        rounding_step=None,
        formula_version_id=formula_id,
        formula_version_number=1,
        formula_ast=ast,
        evaluation_timeout_ms=1000,
        variables=(_build_variable("purchase_price_rub", VariableScope.SKU_INPUT),),
        global_values={},
        global_value_set_at={},
        category_values={},
        supplier_values={},
        settings_versions=(),
    )


# ---------------------------------------------------------------------------
# CAT-011 regression — executor wiring must accept the real callable.
# ---------------------------------------------------------------------------


class TestRecomputeServiceExecutorWiring:
    """Locks the CAT-011 fix in place.

    The bug: ``loop.run_in_executor(None, recompute_sku_pricing, inputs,
    scope, None)`` was called positionally even though
    ``recompute_sku_pricing`` declares ``now`` as keyword-only —
    raising ``TypeError: takes 2 positional arguments but 3 were given``
    on every recompute attempt in production. The fix wraps the call
    with ``functools.partial`` so kwargs flow through.

    A pure-domain test against ``recompute_sku_pricing`` directly would
    NOT have caught this — the regression lived strictly in the
    ``run_in_executor`` adapter. This test exercises that adapter
    end-to-end (real loop, real executor, real pure function).
    """

    @pytest.mark.asyncio
    async def test_recompute_one_routes_through_executor_to_apply_port(self) -> None:
        formula_id = uuid.uuid4()
        inputs = _build_inputs()
        scope = _build_scope(formula_id)
        apply_port = _SpyApplyPort()

        service = RecomputeSkuPricingService(
            input_reader=_StubInputReader(inputs),
            scope_reader=_StubScopeReader(scope),
            apply_port=apply_port,
            logger=structlog.get_logger("test"),
        )

        outcome = await service.recompute_one(sku_id=inputs.sku_id)

        # If the executor wiring regressed, recompute_sku_pricing would
        # raise TypeError before any apply is reached.
        assert outcome == "priced"
        assert len(apply_port.success_calls) == 1
        assert len(apply_port.failure_calls) == 0

        applied = apply_port.success_calls[0]
        assert applied.sku_id == inputs.sku_id
        assert applied.expected_version == inputs.version
        # Identity formula: selling == purchase (in minor units = 100 * 100).
        assert applied.selling_price_minor == 10000
        assert applied.selling_currency == "RUB"
        assert applied.formula_version_id == formula_id

    @pytest.mark.asyncio
    async def test_recompute_one_skips_when_input_reader_returns_none(self) -> None:
        """``read_one`` returning None (locked or deleted) must short-circuit
        without touching the executor or apply port."""
        apply_port = _SpyApplyPort()
        service = RecomputeSkuPricingService(
            input_reader=_StubInputReader(None),
            scope_reader=_StubScopeReader(None),
            apply_port=apply_port,
            logger=structlog.get_logger("test"),
        )

        outcome = await service.recompute_one(sku_id=uuid.uuid4())

        assert outcome == "noop"
        assert apply_port.success_calls == []
        assert apply_port.failure_calls == []

    @pytest.mark.asyncio
    async def test_recompute_one_records_unconfigured_when_scope_missing(self) -> None:
        """Empty scope (no published formula / no supplier-type mapping)
        flows the failure path through ``apply_failure``."""
        inputs = _build_inputs()
        apply_port = _SpyApplyPort()
        service = RecomputeSkuPricingService(
            input_reader=_StubInputReader(inputs),
            scope_reader=_StubScopeReader(None),
            apply_port=apply_port,
            logger=structlog.get_logger("test"),
        )

        outcome = await service.recompute_one(sku_id=inputs.sku_id)

        assert outcome == "context_not_configured"
        assert apply_port.success_calls == []
        assert len(apply_port.failure_calls) == 1
        failure = apply_port.failure_calls[0]
        assert failure.pricing_status == "formula_error"
        assert "not configured" in failure.failure_reason


@pytest.mark.asyncio
async def test_executor_call_uses_keyword_safe_wrapper() -> None:
    """Direct sanity check: the wrapper handed to ``run_in_executor``
    must be invocable with no extra args — exactly what
    ``functools.partial(recompute_sku_pricing, inputs, scope)`` produces.

    If a future refactor passes positional ``None`` again
    (``run_in_executor(None, recompute_sku_pricing, inputs, scope, None)``),
    Python raises ``TypeError`` because ``now`` is keyword-only. This
    smoke test exercises the same call shape the service uses.
    """
    import asyncio
    import functools

    from src.modules.pricing.domain.recompute import recompute_sku_pricing

    inputs = _build_inputs()
    scope = _build_scope(uuid.uuid4())

    loop = asyncio.get_running_loop()
    # Same call shape as RecomputeSkuPricingService — must not raise.
    result = await loop.run_in_executor(
        None,
        functools.partial(recompute_sku_pricing, inputs, scope),
    )
    # Identity formula returns SkuPricingComputed.
    assert result.__class__.__name__ == "SkuPricingComputed"
