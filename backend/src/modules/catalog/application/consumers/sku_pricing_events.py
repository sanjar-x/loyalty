"""TaskIQ consumer for SKU pricing recompute events (CAT-005).

Bridges outbox-delivered ``SKUPricedEvent`` / ``SKUPricingFailedEvent``
to the per-product Redis pub/sub channel that the admin SSE endpoint
streams to clients.
"""

from __future__ import annotations

import uuid

import structlog
from dishka.integrations.taskiq import FromDishka, inject

from src.bootstrap.broker import broker
from src.modules.catalog.infrastructure.services.sku_pricing_pubsub import (
    SkuPricingPubsub,
)

logger = structlog.get_logger(__name__)


@broker.task(
    queue="catalog_sku_pricing_sse",
    exchange="taskiq_rpc_exchange",
    routing_key="catalog.sku_pricing.publish",
    max_retries=2,
    retry_on_error=True,
    timeout=10,
)
@inject
async def publish_sku_pricing_status(
    product_id: str,
    sku_id: str,
    pricing_status: str,
    pubsub: FromDishka[SkuPricingPubsub],
    selling_price_amount: int | None = None,
    selling_currency: str | None = None,
    priced_at: str | None = None,
    priced_failure_reason: str | None = None,
) -> dict:
    """Fan out a single SKU pricing-status event to admin SSE clients.

    Best-effort: if Redis is unavailable, TaskIQ retries up to ``max_retries``
    times. After retries exhausted, the event drops into ``failed_tasks``;
    admin sees stale state until the page is reloaded — recoverable, not
    fatal (HARD-2 monitor will still flag the DLQ growth).
    """
    payload: dict = {
        "skuId": sku_id,
        "pricingStatus": pricing_status,
        "sellingPrice": (
            {"amount": selling_price_amount, "currency": selling_currency}
            if selling_price_amount is not None and selling_currency is not None
            else None
        ),
        "pricedAt": priced_at,
        "pricedFailureReason": priced_failure_reason,
    }
    await pubsub.publish(uuid.UUID(product_id), payload)
    logger.info(
        "sku_pricing_status_published",
        product_id=product_id,
        sku_id=sku_id,
        pricing_status=pricing_status,
    )
    return {"status": "published"}
