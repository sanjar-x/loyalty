"""TaskIQ tasks for autonomous SKU pricing recompute (ADR-005).

Three layers of tasks:

1. ``recompute_sku_pricing_task`` — terminal, per-SKU. Locks the SKU
   row, evaluates the formula, lands the result, commits.
2. Fan-out tasks (``recompute_context_pricing_task``,
   ``recompute_category_pricing_task``,
   ``recompute_supplier_pricing_task``) — enqueue per-SKU jobs in
   batches keyed by the relevant scope.
3. ``rebuild_all_sku_pricing_task`` — admin-triggered, fans out across
   the whole catalog. Used after seeding system variables or doing a
   formula migration.

Outbox handlers (registered below) translate domain events into one of
the above. All tasks are idempotent at the row level via the
``priced_inputs_hash`` short-circuit, so duplicates from at-least-once
delivery never produce a redundant write.
"""

from __future__ import annotations

import uuid

import structlog
from dishka.integrations.taskiq import FromDishka, inject
from sqlalchemy.ext.asyncio import AsyncSession

from src.bootstrap.broker import broker
from src.infrastructure.outbox.relay import register_event_handler
from src.modules.pricing.infrastructure.adapters.sku_pricing_input_reader import (
    SkuPricingInputReader,
)
from src.modules.pricing.infrastructure.services.recompute_service import (
    RecomputeSkuPricingService,
)

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Per-SKU recompute (terminal task)
# ---------------------------------------------------------------------------


@broker.task(
    queue="pricing_recompute",
    exchange="taskiq_rpc_exchange",
    routing_key="pricing.sku.recompute",
    max_retries=3,
    retry_on_error=True,
    timeout=30,
)
@inject
async def recompute_sku_pricing_task(
    sku_id: str,
    *,
    correlation_id: str | None = None,
    service: FromDishka[RecomputeSkuPricingService],
    session: FromDishka[AsyncSession],
) -> dict:
    """Recompute selling price for a single SKU.

    Args:
        sku_id: Catalog SKU UUID (string-encoded for transport).
        correlation_id: Optional trace id propagated end-to-end (HTTP →
            outbox → TaskIQ); recorded in ``sku_pricing_history`` for
            cross-service tracing of "why did this price land".

    Returns:
        ``{"sku_id": ..., "status": ...}`` for observability.
    """
    sku_uuid = uuid.UUID(sku_id)
    status = await service.recompute_one(sku_uuid, correlation_id=correlation_id)
    await session.commit()
    return {"sku_id": sku_id, "status": status}


# ---------------------------------------------------------------------------
# Fan-out tasks
# ---------------------------------------------------------------------------


@broker.task(
    queue="pricing_recompute",
    exchange="taskiq_rpc_exchange",
    routing_key="pricing.context.fanout",
    max_retries=2,
    retry_on_error=True,
    timeout=300,  # 5 min — fan-out across a large catalog
)
@inject
async def recompute_context_pricing_task(
    context_id: str,
    *,
    reader: FromDishka[SkuPricingInputReader],
) -> dict:
    """Fan out per-SKU recompute jobs for every SKU in a context.

    Triggered by ``FormulaPublishedEvent`` /
    ``PricingContextGlobalValueSetEvent`` /
    ``FormulaRolledBackEvent`` — anything that invalidates the context's
    pricing inputs en masse.
    """
    return await _fanout(
        reader.iter_by_context(uuid.UUID(context_id)),
        scope_label="context",
        scope_id=context_id,
    )


@broker.task(
    queue="pricing_recompute",
    exchange="taskiq_rpc_exchange",
    routing_key="pricing.category.fanout",
    max_retries=2,
    retry_on_error=True,
    timeout=300,
)
@inject
async def recompute_category_pricing_task(
    category_id: str,
    *,
    reader: FromDishka[SkuPricingInputReader],
) -> dict:
    """Fan out per-SKU recompute for every SKU in a category."""
    return await _fanout(
        reader.iter_by_category(uuid.UUID(category_id)),
        scope_label="category",
        scope_id=category_id,
    )


@broker.task(
    queue="pricing_recompute",
    exchange="taskiq_rpc_exchange",
    routing_key="pricing.supplier.fanout",
    max_retries=2,
    retry_on_error=True,
    timeout=300,
)
@inject
async def recompute_supplier_pricing_task(
    supplier_id: str,
    *,
    reader: FromDishka[SkuPricingInputReader],
) -> dict:
    """Fan out per-SKU recompute for every SKU owned by a supplier."""
    return await _fanout(
        reader.iter_by_supplier(uuid.UUID(supplier_id)),
        scope_label="supplier",
        scope_id=supplier_id,
    )


async def _fanout(
    batches,
    *,
    scope_label: str,
    scope_id: str,
    correlation_id: str | None = None,
) -> dict:
    """Iterate batches of SKU inputs and enqueue per-SKU tasks."""
    enqueued = 0
    async for batch in batches:
        for inputs in batch:
            kicker = recompute_sku_pricing_task.kicker().with_labels(
                fanout_scope=scope_label,
                fanout_id=scope_id,
                **_build_labels(correlation_id),
            )
            await kicker.kiq(  # ty:ignore[no-matching-overload]
                sku_id=str(inputs.sku_id),
                correlation_id=correlation_id,
            )
            enqueued += 1
    logger.info(
        "pricing_fanout_completed",
        scope=scope_label,
        scope_id=scope_id,
        enqueued=enqueued,
    )
    return {"scope": scope_label, "scope_id": scope_id, "enqueued": enqueued}


# ---------------------------------------------------------------------------
# Outbox event handlers — translate domain events into TaskIQ kicks.
# ---------------------------------------------------------------------------


def _build_labels(correlation_id: str | None) -> dict[str, str]:
    return {"correlation_id": correlation_id} if correlation_id else {}


async def _handle_sku_purchase_price_updated(
    payload: dict, correlation_id: str | None = None
) -> None:
    sku_id = payload.get("sku_id")
    if not sku_id:
        logger.warning("sku_purchase_price_updated_missing_sku_id", payload=payload)
        return
    await (
        recompute_sku_pricing_task.kicker()  # ty: ignore[no-matching-overload]
        .with_labels(**_build_labels(correlation_id))
        .kiq(
            sku_id=str(sku_id),
            correlation_id=correlation_id,
        )
    )


async def _handle_formula_published(
    payload: dict, correlation_id: str | None = None
) -> None:
    context_id = payload.get("context_id")
    if not context_id:
        logger.warning("formula_published_missing_context_id", payload=payload)
        return
    await (
        recompute_context_pricing_task.kicker()
        .with_labels(**_build_labels(correlation_id))
        .kiq(context_id=str(context_id))  # ty:ignore[no-matching-overload]
    )


async def _handle_pricing_context_global_value_set(
    payload: dict, correlation_id: str | None = None
) -> None:
    # FX-rate updates flow through here. Treat any global value change
    # as cause for a context-wide recompute — the cost is per-SKU
    # idempotent so unchanged inputs short-circuit at the row level.
    context_id = payload.get("context_id")
    if not context_id:
        logger.warning(
            "pricing_context_global_value_set_missing_context_id", payload=payload
        )
        return
    await (
        recompute_context_pricing_task.kicker()
        .with_labels(**_build_labels(correlation_id))
        .kiq(context_id=str(context_id))  # ty:ignore[no-matching-overload]
    )


async def _handle_category_pricing_settings_updated(
    payload: dict, correlation_id: str | None = None
) -> None:
    category_id = payload.get("category_id")
    if not category_id:
        logger.warning(
            "category_pricing_settings_updated_missing_category_id", payload=payload
        )
        return
    await (
        recompute_category_pricing_task.kicker()
        .with_labels(**_build_labels(correlation_id))
        .kiq(category_id=str(category_id))  # ty:ignore[no-matching-overload]
    )


async def _handle_supplier_pricing_settings_updated(
    payload: dict, correlation_id: str | None = None
) -> None:
    supplier_id = payload.get("supplier_id")
    if not supplier_id:
        logger.warning(
            "supplier_pricing_settings_updated_missing_supplier_id", payload=payload
        )
        return
    await (
        recompute_supplier_pricing_task.kicker()
        .with_labels(**_build_labels(correlation_id))
        .kiq(supplier_id=str(supplier_id))  # ty:ignore[no-matching-overload]
    )


# Register all handlers. Imports of ``src.modules.pricing.infrastructure.tasks``
# trigger registration; the application bootstrap imports this module
# alongside ``src.infrastructure.outbox.tasks`` so the relay sees these
# event types from the very first poll.
register_event_handler(
    "SKUPurchasePriceUpdatedEvent", _handle_sku_purchase_price_updated
)
register_event_handler("FormulaPublishedEvent", _handle_formula_published)
register_event_handler("FormulaRolledBackEvent", _handle_formula_published)
register_event_handler(
    "PricingContextGlobalValueSetEvent",
    _handle_pricing_context_global_value_set,
)
register_event_handler(
    "CategoryPricingSettingsUpdatedEvent",
    _handle_category_pricing_settings_updated,
)
register_event_handler(
    "CategoryPricingSettingsCreatedEvent",
    _handle_category_pricing_settings_updated,
)
register_event_handler(
    "SupplierPricingSettingsUpdatedEvent",
    _handle_supplier_pricing_settings_updated,
)
register_event_handler(
    "SupplierPricingSettingsCreatedEvent",
    _handle_supplier_pricing_settings_updated,
)


__all__ = [
    "recompute_category_pricing_task",
    "recompute_context_pricing_task",
    "recompute_sku_pricing_task",
    "recompute_supplier_pricing_task",
]
