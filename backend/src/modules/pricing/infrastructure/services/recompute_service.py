"""Orchestrates per-SKU pricing recompute (ADR-005, ADR-005a).

Wires three anti-corruption ports -- pricing-side input reader and
scope reader plus the **catalog-side** :class:`IInternalSkuPricingApplyPort`
-- and the pure-domain :func:`recompute_sku_pricing` into a single async
entry point. TaskIQ tasks (one per SKU) and the manual admin trigger
both call :meth:`RecomputeSkuPricingService.recompute_one`.

Concurrency model:

* The catalog SKU row is locked twice in independent transactions:
  once by :class:`SkuPricingInputReader` (``SELECT ... FOR UPDATE
  SKIP LOCKED``) to serialise duplicate triggers across workers, and
  once again inside the catalog apply command which takes a fresh
  ``FOR UPDATE`` on the owning Product aggregate. Reading + applying
  are deliberately **separate** transactions:

    1. The reader transaction is short-lived and holds the row only
       long enough to snapshot inputs.
    2. The apply transaction holds the aggregate lock during the
       atomic UPDATE + history insert + outbox event flush.

  The optimistic-locking ``expected_version`` is the bridge between
  them: if anything mutates the SKU row between the two locks (admin
  PATCH, another recompute), the apply returns
  :attr:`WriteOutcome.VERSION_CONFLICT` and we retry with bounded
  exponential backoff. After the retry budget is exhausted we persist
  a terminal ``formula_error`` row tagged with
  ``failure_kind="retry_exhausted"`` (ADR-005a Open Issue #3) so
  analytics can alert on lock-contention rates separately from
  formula bug rates.

* Formula evaluation runs in the default thread-pool executor under
  ``asyncio.wait_for`` to honour the context's CPU budget without
  starving the event loop.

* All writes (SKU UPDATE, ``sku_pricing_history`` row, outbox events)
  happen inside the catalog apply command's UoW. This service is
  transaction-agnostic -- it never touches a session directly.

Outcome handling is exhaustive: each return from the catalog port is
matched against every :class:`WriteOutcome` variant (no implicit
fall-through), so a future fifth variant fails type-check rather than
silently being treated as success.
"""

from __future__ import annotations

import asyncio
import functools
import random
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import assert_never

from src.modules.catalog.domain.interfaces import (
    IInternalSkuPricingApplyPort,
    SkuPricingApplyRequest,
    SkuPricingFailureRequest,
    WriteOutcome,
)
from src.modules.pricing.domain.interfaces import (
    ISkuPricingInputReader,
    ISkuPricingScopeReader,
)
from src.modules.pricing.domain.recompute import (
    SkuPricingComputed,
    SkuPricingFailed,
    recompute_sku_pricing,
)
from src.shared.interfaces.logger import ILogger

# Bounded retry parameters for optimistic-lock conflicts.
_RETRY_MAX_ATTEMPTS = 3
_RETRY_BACKOFF_BASE_MS = 50
_RETRY_BACKOFF_JITTER_MS = 25


class RecomputeSkuPricingService:
    """High-level orchestrator for one-SKU pricing recompute (ADR-005)."""

    def __init__(
        self,
        input_reader: ISkuPricingInputReader,
        scope_reader: ISkuPricingScopeReader,
        apply_port: IInternalSkuPricingApplyPort,
        logger: ILogger,
    ) -> None:
        self._input_reader = input_reader
        self._scope_reader = scope_reader
        self._apply_port = apply_port
        self._logger = logger.bind(service="RecomputeSkuPricingService")

    async def recompute_one(
        self,
        sku_id: uuid.UUID,
        *,
        correlation_id: str | None = None,
    ) -> str:
        """Recompute one SKU's selling price."""
        log = self._logger.bind(
            sku_id=str(sku_id),
            correlation_id=correlation_id,
        )

        for attempt in range(_RETRY_MAX_ATTEMPTS):
            outcome = await self._attempt_recompute(
                sku_id=sku_id,
                correlation_id=correlation_id,
                log=log.bind(attempt=attempt + 1),
            )
            if outcome.kind != "version_conflict":
                return outcome.status

            if attempt + 1 < _RETRY_MAX_ATTEMPTS:
                delay_ms = _RETRY_BACKOFF_BASE_MS * (2**attempt) + random.uniform(
                    0, _RETRY_BACKOFF_JITTER_MS
                )
                await asyncio.sleep(delay_ms / 1000.0)

        log.warning("recompute_lock_thrashing", attempts=_RETRY_MAX_ATTEMPTS)
        await self._record_retry_exhausted_failure(
            sku_id=sku_id,
            correlation_id=correlation_id,
            log=log,
        )
        return "formula_error"

    async def _attempt_recompute(
        self,
        *,
        sku_id: uuid.UUID,
        correlation_id: str | None,
        log: ILogger,
    ) -> _AttemptOutcome:
        """One read -> evaluate -> apply pass."""
        inputs = await self._input_reader.read_one(sku_id, lock=True)
        if inputs is None:
            log.info("recompute_skipped", reason="locked_or_deleted")
            return _AttemptOutcome.terminal("noop")

        scope = await self._scope_reader.snapshot_for_sku(inputs)
        if scope is None:
            failure = SkuPricingFailureRequest(
                product_id=inputs.product_id,
                sku_id=sku_id,
                expected_version=inputs.version,
                previous_status=inputs.pricing_status,
                pricing_status="formula_error",
                failure_reason=(
                    "Pricing context not configured for this SKU "
                    "(missing supplier_type -> context mapping or no "
                    "published formula)"
                ),
                correlation_id=correlation_id,
            )
            apply_outcome = await self._apply_port.apply_failure(failure)
            if apply_outcome is WriteOutcome.VERSION_CONFLICT:
                return _AttemptOutcome.conflict()
            log.warning(
                "recompute_unconfigured",
                supplier_type=inputs.supplier_type,
                outcome=apply_outcome.value,
            )
            return _AttemptOutcome.terminal("context_not_configured")

        timeout_s = (
            scope.evaluation_timeout_ms / 1000.0 if scope.evaluation_timeout_ms else 1.0
        )
        loop = asyncio.get_running_loop()
        # CAT-011 — ``recompute_sku_pricing`` declares ``now`` as keyword-only.
        # ``run_in_executor(None, fn, *args)`` cannot pass kwargs, so the
        # previous positional ``None`` triggered ``TypeError: takes 2
        # positional arguments but 3 were given`` for every recompute attempt
        # in production. Wrap with ``functools.partial`` instead — kwargs go
        # through, and we drop the explicit ``None`` since that's already the
        # default (production code never overrides ``now``; tests do).
        try:
            result = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    functools.partial(recompute_sku_pricing, inputs, scope),
                ),
                timeout=timeout_s,
            )
        except TimeoutError:
            failure = SkuPricingFailureRequest(
                product_id=inputs.product_id,
                sku_id=sku_id,
                expected_version=inputs.version,
                previous_status=inputs.pricing_status,
                pricing_status="formula_error",
                failure_reason=(
                    f"Formula evaluation exceeded the configured budget "
                    f"of {int(timeout_s * 1000)}ms"
                ),
                correlation_id=correlation_id,
            )
            apply_outcome = await self._apply_port.apply_failure(failure)
            if apply_outcome is WriteOutcome.VERSION_CONFLICT:
                return _AttemptOutcome.conflict()
            log.warning(
                "recompute_timeout",
                timeout_ms=int(timeout_s * 1000),
                outcome=apply_outcome.value,
            )
            return _AttemptOutcome.terminal("formula_error")

        if isinstance(result, SkuPricingFailed):
            failure = SkuPricingFailureRequest(
                product_id=inputs.product_id,
                sku_id=sku_id,
                expected_version=inputs.version,
                previous_status=inputs.pricing_status,
                pricing_status=result.status,
                failure_reason=result.reason,
                correlation_id=correlation_id,
            )
            apply_outcome = await self._apply_port.apply_failure(failure)
            if apply_outcome is WriteOutcome.VERSION_CONFLICT:
                return _AttemptOutcome.conflict()
            log.info(
                "recompute_failed",
                status=result.status,
                outcome=apply_outcome.value,
            )
            return _AttemptOutcome.terminal(result.status)

        assert isinstance(result, SkuPricingComputed)

        # Convert the formula-evaluator's Decimal-major-units to integer
        # minor units (kopecks) using the target currency's ISO 4217
        # ``minor_unit`` precision, captured by the scope snapshot.
        # Doing the conversion here keeps the catalog-side apply
        # handler free of a ``catalog -> geo`` cross-module import: the
        # handler stores what it's given.
        digits = scope.target_currency_minor_unit
        selling_price_minor = int(
            (result.selling_price * Decimal(10) ** digits).to_integral_value()
        )

        success = SkuPricingApplyRequest(
            product_id=inputs.product_id,
            sku_id=sku_id,
            expected_version=inputs.version,
            previous_status=inputs.pricing_status,
            selling_price_minor=selling_price_minor,
            selling_currency=result.selling_currency,
            formula_version_id=result.formula_version_id,
            inputs_hash=result.inputs_hash,
            priced_at=datetime.now(UTC),
            correlation_id=correlation_id,
        )
        apply_outcome = await self._apply_port.apply_success(success)

        # Exhaustive match on the outcome -- no implicit fall-through.
        # ``assert_never`` on an unforeseen variant guarantees a
        # type-check failure rather than silent success.
        match apply_outcome:
            case WriteOutcome.VERSION_CONFLICT:
                return _AttemptOutcome.conflict()
            case WriteOutcome.HASH_NOOP:
                log.info(
                    "recompute_noop_already_priced",
                    inputs_hash=result.inputs_hash,
                )
                return _AttemptOutcome.terminal("noop")
            case WriteOutcome.APPLIED:
                log.info(
                    "recompute_priced",
                    selling_price=str(result.selling_price),
                    selling_currency=result.selling_currency,
                    formula_version_id=str(result.formula_version_id),
                )
                return _AttemptOutcome.terminal("priced")
            case WriteOutcome.FAILURE_PERSISTED:
                # apply_success cannot return FAILURE_PERSISTED in a
                # well-formed handler; surface the bug rather than
                # silently treating it as success.
                log.error(
                    "apply_success_returned_failure_persisted",
                    inputs_hash=result.inputs_hash,
                )
                return _AttemptOutcome.terminal("formula_error")
            case _:  # pragma: no cover -- exhaustive guard
                assert_never(apply_outcome)

    async def _record_retry_exhausted_failure(
        self,
        *,
        sku_id: uuid.UUID,
        correlation_id: str | None,
        log: ILogger,
    ) -> None:
        """Persist a ``formula_error`` after all retries failed.

        Tagged with ``failure_kind="retry_exhausted"`` (ADR-005a Open
        Issue #3) so the audit row is distinguishable from formula bug
        failures in analytics dashboards.
        """
        inputs = await self._input_reader.read_one(sku_id, lock=False)
        if inputs is None:
            return
        failure = SkuPricingFailureRequest(
            product_id=inputs.product_id,
            sku_id=sku_id,
            expected_version=inputs.version,
            previous_status=inputs.pricing_status,
            pricing_status="formula_error",
            failure_reason=(
                "Optimistic-lock retries exhausted; admin attention required"
            ),
            failure_kind="retry_exhausted",
            correlation_id=correlation_id,
        )
        outcome = await self._apply_port.apply_failure(failure)
        log.info("retry_exhausted_failure_recorded", outcome=outcome.value)


class _AttemptOutcome:
    """Discriminated union of one recompute-attempt outcome."""

    __slots__ = ("kind", "status")

    def __init__(self, kind: str, status: str) -> None:
        self.kind = kind
        self.status = status

    @classmethod
    def terminal(cls, status: str) -> _AttemptOutcome:
        return cls("terminal", status)

    @classmethod
    def conflict(cls) -> _AttemptOutcome:
        return cls("version_conflict", "version_conflict")
