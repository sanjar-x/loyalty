"""Command handler: bulk-set ``purchase_price`` across many SKUs of one product.

Single transaction over the product aggregate. Each SKU is touched via
:meth:`SKU.set_purchase_price` (ADR-005), which arms the autonomous
recompute pipeline atomically with the business write.

Per-item failures (unknown currency, SKU missing, currency mismatch)
are collected and returned alongside the success counter — the bulk
write does **not** abort on the first error. This matches the admin
workflow where bulk price updates are entered from a spreadsheet and
operators want to see the full failure list rather than fix-and-retry
one-at-a-time.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from redis.exceptions import RedisError

from src.modules.catalog.application.constants import storefront_pdp_cache_key
from src.modules.catalog.domain.events import SKUPurchasePriceUpdatedEvent
from src.modules.catalog.domain.exceptions import ProductNotFoundError
from src.modules.catalog.domain.interfaces import IProductRepository
from src.modules.catalog.domain.value_objects import Money, PurchaseCurrency
from src.shared.exceptions import ValidationError
from src.shared.interfaces.cache import ICacheService
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class BulkSetPurchasePriceItem:
    """One SKU-level update inside a bulk request."""

    sku_id: uuid.UUID
    purchase_price: Money


@dataclass(frozen=True)
class BulkSetPurchasePriceCommand:
    """Apply ``purchase_price`` to many SKUs of one product in one UoW."""

    product_id: uuid.UUID
    items: list[BulkSetPurchasePriceItem]


@dataclass(frozen=True)
class BulkSetPurchasePriceItemError:
    """One SKU failure inside the bulk result."""

    sku_id: uuid.UUID
    error_code: str
    message: str


@dataclass(frozen=True)
class BulkSetPurchasePriceResult:
    """Outcome of a bulk purchase-price update.

    Attributes:
        updated_count: Number of SKUs where the purchase_price actually
            changed (set_purchase_price returns True only on real diffs).
        unchanged_count: Number of SKUs where the supplied value matched
            the stored one (idempotent re-submit).
        errors: Per-SKU failures (skipped, did not abort the batch).
    """

    updated_count: int
    unchanged_count: int
    errors: list[BulkSetPurchasePriceItemError] = field(default_factory=list)


class BulkSetPurchasePriceHandler:
    """Apply purchase-price updates to many SKUs in a single transaction."""

    def __init__(
        self,
        product_repo: IProductRepository,
        uow: IUnitOfWork,
        cache: ICacheService,
        logger: ILogger,
    ) -> None:
        self._product_repo = product_repo
        self._uow = uow
        self._cache = cache
        self._logger = logger.bind(handler="BulkSetPurchasePriceHandler")

    async def handle(
        self, command: BulkSetPurchasePriceCommand
    ) -> BulkSetPurchasePriceResult:
        if not command.items:
            raise ValidationError(
                message="items must contain at least one entry",
                error_code="BULK_PURCHASE_PRICE_EMPTY",
            )

        updated = 0
        unchanged = 0
        errors: list[BulkSetPurchasePriceItemError] = []

        async with self._uow:
            product = await self._product_repo.get_for_update_with_variants(
                command.product_id
            )
            if product is None:
                raise ProductNotFoundError(product_id=command.product_id)

            for item in command.items:
                sku = product.find_sku(item.sku_id)
                if sku is None:
                    errors.append(
                        BulkSetPurchasePriceItemError(
                            sku_id=item.sku_id,
                            error_code="SKU_NOT_FOUND",
                            message="SKU does not belong to this product",
                        )
                    )
                    continue

                try:
                    purchase_currency = PurchaseCurrency(item.purchase_price.currency)
                except ValueError:
                    errors.append(
                        BulkSetPurchasePriceItemError(
                            sku_id=item.sku_id,
                            error_code="INVALID_PURCHASE_CURRENCY",
                            message=(
                                f"purchase_price.currency '{item.purchase_price.currency}'"
                                " is not supported (use RUB or CNY)"
                            ),
                        )
                    )
                    continue

                try:
                    changed = sku.set_purchase_price(
                        purchase_price=item.purchase_price,
                        purchase_currency=purchase_currency,
                    )
                except ValueError as exc:
                    errors.append(
                        BulkSetPurchasePriceItemError(
                            sku_id=item.sku_id,
                            error_code="INVALID_PURCHASE_PRICE",
                            message=str(exc),
                        )
                    )
                    continue

                if changed:
                    # CAT-010 — emit on aggregate root so the recompute
                    # pipeline picks up via the outbox relay. Without this
                    # SKU stays in PENDING forever.
                    product.add_domain_event(
                        SKUPurchasePriceUpdatedEvent(
                            product_id=product.id,
                            variant_id=sku.variant_id,
                            sku_id=sku.id,
                            purchase_price_amount=item.purchase_price.amount,
                            purchase_currency=purchase_currency.value,
                            aggregate_id=str(product.id),
                        )
                    )
                    updated += 1
                else:
                    unchanged += 1

            if updated > 0:
                await self._product_repo.update(product)
                self._uow.register_aggregate(product)
                await self._uow.commit()

        if updated > 0:
            try:
                await self._cache.delete(storefront_pdp_cache_key(product.slug))
            except RedisError as exc:  # pragma: no cover
                # Stale PDP cache means customers see the OLD purchase price
                # for every SKU just bulk-updated until TTL — alert-worthy
                # (CAT-018 H5).
                self._logger.error(
                    "pdp_cache_invalidation_failed",
                    product_id=str(command.product_id),
                    slug=product.slug,
                    error=str(exc),
                )

        # Distinguish "all idempotent" (unchanged>0, errors=0) from
        # "all failed" (unchanged=0, errors>0) at the log level —
        # otherwise the ``info`` line below treats both as benign and
        # operations cannot tell the difference (CAT-018 H4).
        if updated == 0 and errors and unchanged == 0:
            self._logger.warning(
                "bulk_purchase_price_all_failed",
                product_id=str(command.product_id),
                errors=len(errors),
            )

        self._logger.info(
            "Bulk purchase-price applied",
            product_id=str(command.product_id),
            updated=updated,
            unchanged=unchanged,
            errors=len(errors),
        )
        return BulkSetPurchasePriceResult(
            updated_count=updated,
            unchanged_count=unchanged,
            errors=errors,
        )
