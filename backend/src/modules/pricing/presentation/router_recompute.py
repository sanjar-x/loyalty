"""Admin endpoints for manually triggering SKU pricing recompute (ADR-005).

The autonomous pipeline already covers every routine input change via
outbox + TaskIQ. These endpoints exist for two operational scenarios:

* **Diagnostic re-run** — admin wants to re-evaluate one SKU (or one
  context) immediately after editing pricing inputs, without waiting
  for the outbox relay's polling cycle. The synchronous endpoint
  returns the resulting status straight away.
* **Bulk rebuild** — after seeding system variables for the first
  time or migrating a formula across many contexts, admins fan out
  per-SKU jobs by hand. The fan-out endpoints enqueue TaskIQ jobs
  and return ``202 Accepted``.

All endpoints require ``pricing:admin``.
"""

from __future__ import annotations

import uuid

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from src.modules.identity.presentation.dependencies import RequirePermission
from src.modules.pricing.infrastructure.services.recompute_service import (
    RecomputeSkuPricingService,
)

pricing_recompute_router = APIRouter(
    prefix="/pricing/recompute",
    tags=["Pricing Recompute (admin)"],
    route_class=DishkaRoute,
)


class RecomputeSkuResponse(BaseModel):
    """Synchronous per-SKU recompute outcome."""

    sku_id: uuid.UUID
    status: str = Field(
        description=(
            "One of: priced, noop, missing_purchase_price, stale_fx, "
            "formula_error, sku_not_found, context_not_configured"
        )
    )


class RecomputeFanoutResponse(BaseModel):
    """Fan-out request acknowledgement.

    The fan-out task runs asynchronously via TaskIQ; the response only
    confirms enqueue success. Per-SKU progress is observable through
    the relay's structured logs and ``SKU.pricing_status``.
    """

    scope: str
    scope_id: uuid.UUID
    enqueued: bool = True


@pricing_recompute_router.post(
    "/skus/{sku_id}",
    response_model=RecomputeSkuResponse,
    summary="Synchronously recompute a single SKU's selling price",
    dependencies=[Depends(RequirePermission(codename="pricing:admin"))],
)
async def recompute_one_sku(
    sku_id: uuid.UUID,
    service: FromDishka[RecomputeSkuPricingService],
) -> RecomputeSkuResponse:
    """Run the recompute pipeline for one SKU and return the result."""
    status_code = await service.recompute_one(sku_id)
    return RecomputeSkuResponse(sku_id=sku_id, status=status_code)


@pricing_recompute_router.post(
    "/contexts/{context_id}",
    response_model=RecomputeFanoutResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Fan out recompute for every SKU in a pricing context",
    dependencies=[Depends(RequirePermission(codename="pricing:admin"))],
)
async def recompute_context(context_id: uuid.UUID) -> RecomputeFanoutResponse:
    """Enqueue per-SKU recompute jobs for the context.

    Importing the TaskIQ task lazily keeps this endpoint testable
    without an active broker — the FastAPI server itself does not
    register pricing tasks (the worker does).
    """
    from src.modules.pricing.infrastructure.tasks import (
        recompute_context_pricing_task,
    )

    await (
        recompute_context_pricing_task.kicker().kiq(context_id=str(context_id))  # ty:ignore[no-matching-overload]
    )
    return RecomputeFanoutResponse(scope="context", scope_id=context_id)


@pricing_recompute_router.post(
    "/categories/{category_id}",
    response_model=RecomputeFanoutResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Fan out recompute for every SKU in a category",
    dependencies=[Depends(RequirePermission(codename="pricing:admin"))],
)
async def recompute_category(category_id: uuid.UUID) -> RecomputeFanoutResponse:
    from src.modules.pricing.infrastructure.tasks import (
        recompute_category_pricing_task,
    )

    await (
        recompute_category_pricing_task.kicker().kiq(category_id=str(category_id))  # ty:ignore[no-matching-overload]
    )
    return RecomputeFanoutResponse(scope="category", scope_id=category_id)


@pricing_recompute_router.post(
    "/suppliers/{supplier_id}",
    response_model=RecomputeFanoutResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Fan out recompute for every SKU owned by a supplier",
    dependencies=[Depends(RequirePermission(codename="pricing:admin"))],
)
async def recompute_supplier(supplier_id: uuid.UUID) -> RecomputeFanoutResponse:
    from src.modules.pricing.infrastructure.tasks import (
        recompute_supplier_pricing_task,
    )

    await (
        recompute_supplier_pricing_task.kicker().kiq(supplier_id=str(supplier_id))  # ty:ignore[no-matching-overload]
    )
    return RecomputeFanoutResponse(scope="supplier", scope_id=supplier_id)
