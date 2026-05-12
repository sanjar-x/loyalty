"""
Command handler: apply a SKU pricing recompute result on the catalog side.

Implements :class:`IInternalSkuPricingApplyPort` per ADR-005a inversion.
The pricing recompute service computes the selling price (or a failure
status) and hands the result here; this handler:

* takes ``FOR UPDATE`` on the owning Product aggregate (catalog UoW
  convention),
* short-circuits on ``inputs_hash`` match (HASH_NOOP — at-least-once
  delivery idempotency),
* checks optimistic ``expected_version`` (VERSION_CONFLICT — caller
  retries),
* mutates the SKU child entity through its domain mutators
  (``SKU.apply_pricing_result`` / ``SKU.mark_pricing_failed``),
* persists the audit row through :class:`IPricingHistoryRepository`,
* emits the appropriate domain event (``SKUPricedEvent`` /
  ``SKUPricingFailedEvent``) on the Product aggregate,
* commits the UoW.

Sits in ``application/commands/`` because invocation IS a write
operation; the call source (pricing recompute service through the
port) is a domain-internal handoff rather than an HTTP/CLI command,
but the structural shape (UoW, FOR UPDATE, persist, emit) is identical
to other catalog write commands.
"""

from __future__ import annotations

from src.modules.catalog.domain.events import SKUPricedEvent, SKUPricingFailedEvent
from src.modules.catalog.domain.interfaces import (
    IInternalSkuPricingApplyPort,
    IPricingHistoryRepository,
    IProductRepository,
    PricingHistoryEntry,
    SkuPricingApplyRequest,
    SkuPricingFailureRequest,
    WriteOutcome,
)
from src.modules.catalog.domain.value_objects import Money, SkuPricingStatus
from shared.interfaces.logger import ILogger
from shared.interfaces.uow import IUnitOfWork


class ApplySkuPricingResultHandler(IInternalSkuPricingApplyPort):
    """Catalog-side handler for the pricing recompute apply path (ADR-005a)."""

    def __init__(
        self,
        product_repo: IProductRepository,
        history_repo: IPricingHistoryRepository,
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
        self._product_repo = product_repo
        self._history_repo = history_repo
        self._uow = uow
        self._logger = logger.bind(handler="ApplySkuPricingResultHandler")

    async def apply_success(self, request: SkuPricingApplyRequest) -> WriteOutcome:
        log = self._logger.bind(op="apply_success", sku_id=str(request.sku_id))

        async with self._uow:
            product = await self._product_repo.get_for_update_with_variants(
                request.product_id
            )
            if product is None:
                log.warning("product_not_found", product_id=str(request.product_id))
                return WriteOutcome.VERSION_CONFLICT
            sku = product.find_sku(request.sku_id)
            if sku is None:
                log.warning("sku_not_found")
                return WriteOutcome.VERSION_CONFLICT

            # Hash-first shortcut: identical inputs already produced this
            # row's PRICED state -- idempotent no-op regardless of any
            # version drift, no row mutation, no audit row, no event.
            if (
                sku.priced_inputs_hash == request.inputs_hash
                and sku.pricing_status is SkuPricingStatus.PRICED
            ):
                log.info("hash_noop", inputs_hash=request.inputs_hash)
                return WriteOutcome.HASH_NOOP

            if sku.version != request.expected_version:
                log.info(
                    "version_conflict",
                    expected=request.expected_version,
                    actual=sku.version,
                )
                return WriteOutcome.VERSION_CONFLICT

            money = Money(
                amount=request.selling_price_minor,
                currency=request.selling_currency,
            )
            sku.apply_pricing_result(
                selling_price=money,
                formula_version_id=request.formula_version_id,
                inputs_hash=request.inputs_hash,
                priced_at=request.priced_at,
            )

            await self._product_repo.update(product)
            await self._history_repo.add(
                PricingHistoryEntry(
                    sku_id=request.sku_id,
                    new_status=SkuPricingStatus.PRICED.value,
                    previous_status=request.previous_status,
                    selling_price=request.selling_price_minor,
                    selling_currency=request.selling_currency,
                    formula_version_id=request.formula_version_id,
                    inputs_hash=request.inputs_hash,
                    failure_reason=None,
                    failure_kind=None,
                    correlation_id=request.correlation_id,
                )
            )
            product.add_domain_event(
                SKUPricedEvent(
                    product_id=request.product_id,
                    variant_id=sku.variant_id,
                    sku_id=request.sku_id,
                    selling_price_amount=request.selling_price_minor,
                    selling_currency=request.selling_currency,
                    formula_version_id=request.formula_version_id,
                    inputs_hash=request.inputs_hash,
                )
            )
            self._uow.register_aggregate(product)
            await self._uow.commit()

        log.info("applied", inputs_hash=request.inputs_hash)
        return WriteOutcome.APPLIED

    async def apply_failure(self, request: SkuPricingFailureRequest) -> WriteOutcome:
        log = self._logger.bind(
            op="apply_failure",
            sku_id=str(request.sku_id),
            pricing_status=request.pricing_status,
            failure_kind=request.failure_kind,
        )

        async with self._uow:
            product = await self._product_repo.get_for_update_with_variants(
                request.product_id
            )
            if product is None:
                log.warning("product_not_found", product_id=str(request.product_id))
                return WriteOutcome.VERSION_CONFLICT
            sku = product.find_sku(request.sku_id)
            if sku is None:
                log.warning("sku_not_found")
                return WriteOutcome.VERSION_CONFLICT

            if sku.version != request.expected_version:
                log.info(
                    "version_conflict",
                    expected=request.expected_version,
                    actual=sku.version,
                )
                return WriteOutcome.VERSION_CONFLICT

            # Validate pricing_status string is a real failure state.
            # SKU.mark_pricing_failed will additionally enforce that it
            # is one of {STALE_FX, MISSING_PURCHASE_PRICE, FORMULA_ERROR}.
            status = SkuPricingStatus(request.pricing_status)

            sku.mark_pricing_failed(status=status, reason=request.failure_reason)

            await self._product_repo.update(product)
            await self._history_repo.add(
                PricingHistoryEntry(
                    sku_id=request.sku_id,
                    new_status=status.value,
                    previous_status=request.previous_status,
                    selling_price=None,
                    selling_currency=None,
                    formula_version_id=None,
                    inputs_hash=None,
                    failure_reason=request.failure_reason,
                    failure_kind=request.failure_kind,
                    correlation_id=request.correlation_id,
                )
            )
            product.add_domain_event(
                SKUPricingFailedEvent(
                    product_id=request.product_id,
                    variant_id=sku.variant_id,
                    sku_id=request.sku_id,
                    pricing_status=status.value,
                    failure_reason=request.failure_reason,
                )
            )
            self._uow.register_aggregate(product)
            await self._uow.commit()

        log.info("failure_persisted")
        return WriteOutcome.FAILURE_PERSISTED
