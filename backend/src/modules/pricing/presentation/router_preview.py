"""FastAPI router for on-demand price preview.

FRD §Price Computation — read-side endpoint that wires the variable resolver
and formula evaluator without persisting anything.
"""

from __future__ import annotations

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Depends, status

from src.modules.identity.presentation.dependencies import RequirePermission
from src.modules.pricing.application.queries.preview_price import (
    PreviewPriceHandler,
    PreviewPriceQuery,
)
from src.modules.pricing.presentation.schemas import (
    PreviewPriceRequest,
    PreviewPriceResponse,
)

pricing_preview_router = APIRouter(
    prefix="/pricing",
    tags=["Pricing Preview"],
    route_class=DishkaRoute,
)


@pricing_preview_router.post(
    "/preview",
    response_model=PreviewPriceResponse,
    status_code=status.HTTP_200_OK,
    summary="Preview a product's computed price",
    dependencies=[Depends(RequirePermission(codename="pricing:read"))],
)
async def preview_price(
    body: PreviewPriceRequest,
    handler: FromDishka[PreviewPriceHandler],
) -> PreviewPriceResponse:
    result = await handler.handle(
        PreviewPriceQuery(
            product_id=body.product_id,
            category_id=body.category_id,
            context_id=body.context_id,
            supplier_id=body.supplier_id,
        )
    )
    return PreviewPriceResponse(
        final_price=result.final_price,
        components=result.components,
        formula_version_id=result.formula_version_id,
        formula_version_number=result.formula_version_number,
        context_id=result.context_id,
    )
