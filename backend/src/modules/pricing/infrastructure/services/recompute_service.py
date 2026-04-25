"""Orchestrates per-SKU pricing recompute (ADR-005).

Wires the three anti-corruption ports (input reader, scope reader,
result writer) and the pure-domain :func:`recompute_sku_pricing` into a
single async entry point. TaskIQ tasks (one per SKU) and the manual
admin trigger both call :meth:`RecomputeSkuPricingService.recompute_one`.

Concurrency model:

* The catalog SKU row is locked via ``SELECT … FOR UPDATE SKIP LOCKED``
  inside this service so concurrent triggers serialise per-SKU. Other
  SKUs proceed in parallel.
* Formula evaluation runs in the default thread-pool executor under
  ``asyncio.wait_for`` to honour the context's CPU budget without
  starving the event loop.
* All writes (SKU update + commit) live in the caller's UoW; the
  service is transaction-agnostic.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime

from src.modules.pricing.domain.interfaces import (
    ISkuPricingInputReader,
    ISkuPricingResultWriter,
    ISkuPricingScopeReader,
    SkuPricingApplyRequest,
    SkuPricingFailureRequest,
)
from src.modules.pricing.domain.recompute import (
    SkuPricingComputed,
    SkuPricingFailed,
    recompute_sku_pricing,
)
from src.shared.interfaces.logger import ILogger


class RecomputeSkuPricingService:
    """High-level orchestrator for one-SKU pricing recompute (ADR-005)."""

    def __init__(
        self,
        input_reader: ISkuPricingInputReader,
        scope_reader: ISkuPricingScopeReader,
        result_writer: ISkuPricingResultWriter,
        logger: ILogger,
    ) -> None:
        self._input_reader = input_reader
        self._scope_reader = scope_reader
        self._result_writer = result_writer
        self._logger = logger.bind(service="RecomputeSkuPricingService")

    async def recompute_one(
        self,
        sku_id: uuid.UUID,
        *,
        correlation_id: str | None = None,
    ) -> str:
        """Recompute one SKU's selling price.

        Returns a short status code suitable for logs and TaskIQ result
        payloads:

        * ``"priced"`` — fresh selling price written.
        * ``"noop"`` — inputs unchanged or row already at this state.
        * ``"missing_purchase_price"`` / ``"stale_fx"`` / ``"formula_error"``
          — failure status persisted on the SKU.
        * ``"sku_not_found"`` — SKU absent or soft-deleted.
        * ``"context_not_configured"`` — supplier_type or context mapping
          is incomplete; admin attention required.
        """
        log = self._logger.bind(sku_id=str(sku_id))

        # Lock the SKU row so concurrent triggers serialise. SKIP LOCKED
        # makes a duplicate task that lands while a prior one is still
        # working return ``None`` here — the in-flight worker is the
        # source of truth for that SKU.
        inputs = await self._input_reader.read_one(sku_id, lock=True)
        if inputs is None:
            log.info("recompute_skipped", reason="locked_or_deleted")
            return "noop"

        scope = await self._scope_reader.snapshot_for_sku(inputs)
        if scope is None:
            # No published formula / no supplier_type → context mapping.
            # We surface this as MISSING_PURCHASE_PRICE-equivalent so the
            # SKU drops out of the storefront until admins wire it.
            failure = SkuPricingFailureRequest(
                sku_id=sku_id,
                expected_version=inputs.version,
                previous_status=inputs.pricing_status,
                pricing_status="formula_error",
                failure_reason=(
                    "Pricing context not configured for this SKU "
                    "(missing supplier_type → context mapping or no "
                    "published formula)"
                ),
                correlation_id=correlation_id,
            )
            await self._result_writer.apply_failure(failure)
            log.warning("recompute_unconfigured", supplier_type=inputs.supplier_type)
            return "context_not_configured"

        # Formula evaluation can be CPU-bound on adversarial ASTs; run
        # under the context's timeout in the default executor. Defensive
        # fallback to 1s when the context has no recorded budget so a
        # NULL never crashes division.
        timeout_s = (
            scope.evaluation_timeout_ms / 1000.0 if scope.evaluation_timeout_ms else 1.0
        )
        loop = asyncio.get_running_loop()
        try:
            result = await asyncio.wait_for(
                loop.run_in_executor(None, recompute_sku_pricing, inputs, scope, None),
                timeout=timeout_s,
            )
        except TimeoutError:
            failure = SkuPricingFailureRequest(
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
            await self._result_writer.apply_failure(failure)
            log.warning("recompute_timeout", timeout_ms=int(timeout_s * 1000))
            return "formula_error"

        if isinstance(result, SkuPricingFailed):
            failure = SkuPricingFailureRequest(
                sku_id=sku_id,
                expected_version=inputs.version,
                previous_status=inputs.pricing_status,
                pricing_status=result.status,
                failure_reason=result.reason,
                correlation_id=correlation_id,
            )
            applied = await self._result_writer.apply_failure(failure)
            log.info(
                "recompute_failed",
                status=result.status,
                applied=applied,
            )
            return result.status

        assert isinstance(result, SkuPricingComputed)
        success = SkuPricingApplyRequest(
            sku_id=sku_id,
            expected_version=inputs.version,
            previous_status=inputs.pricing_status,
            selling_price=result.selling_price,
            selling_currency=result.selling_currency,
            formula_version_id=result.formula_version_id,
            inputs_hash=result.inputs_hash,
            priced_at=datetime.now(UTC),
            correlation_id=correlation_id,
        )
        applied = await self._result_writer.apply_success(success)
        if not applied:
            log.info("recompute_noop_already_priced", inputs_hash=result.inputs_hash)
            return "noop"
        log.info(
            "recompute_priced",
            selling_price=str(result.selling_price),
            selling_currency=result.selling_currency,
            formula_version_id=str(result.formula_version_id),
        )
        return "priced"
