"""FastAPI router for on-demand price preview.

FRD §Price Computation — read-side endpoint that wires the variable resolver
and formula evaluator without persisting anything.
"""

from __future__ import annotations

from dishka.integrations.fastapi import DishkaRoute, FromDishka, inject
from fastapi import APIRouter, Depends, status

from src.modules.identity.presentation.dependencies import Auth, RequirePermission
from src.modules.pricing.application.queries.preview_price import (
    PreviewPriceHandler,
    PreviewPriceQuery,
)
from src.modules.pricing.application.queries.preview_sku_pricing import (
    PreviewSkuPricingHandler,
    PreviewSkuPricingQuery,
)
from src.modules.pricing.presentation.schemas import (
    FormulaBindingValue,
    PreviewPriceRequest,
    PreviewPriceResponse,
    PreviewSkuPricingRequest,
    PreviewSkuPricingResponse,
)
from shared.interfaces.security import IPermissionResolver

_ADMIN_PERMISSION = "pricing:admin"

pricing_preview_router = APIRouter(
    prefix="/admin/pricing",
    tags=["Admin / Pricing / Preview"],
    route_class=DishkaRoute,
)


@inject
async def _caller_is_pricing_admin(
    auth: Auth,
    resolver: FromDishka[IPermissionResolver],
) -> bool:
    """Non-raising admin check for response shaping."""
    return await resolver.has_permission(auth.session_id, _ADMIN_PERMISSION)


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
    is_admin: bool = Depends(_caller_is_pricing_admin),
) -> PreviewPriceResponse:
    result = await handler.handle(
        PreviewPriceQuery(
            product_id=body.product_id,
            category_id=body.category_id,
            context_id=body.context_id,
            supplier_id=body.supplier_id,
        )
    )
    # Intermediate binding values reveal internal formula structure
    # (markups, VAT, margin composition). Only expose them to pricing:admin;
    # lower-privilege users see only the final price.
    components = result.components if is_admin else {}
    return PreviewPriceResponse(
        final_price=result.final_price,
        components=components,
        formula_version_id=result.formula_version_id,
        formula_version_number=result.formula_version_number,
        context_id=result.context_id,
    )


@pricing_preview_router.post(
    "/preview-sku",
    response_model=PreviewSkuPricingResponse,
    status_code=status.HTTP_200_OK,
    summary="Preview a SKU's selling price for an admin-supplied purchase_price",
    description=(
        "Admin UI calls this as the operator types the purchase price field "
        "(debounced) so the formula-computed selling price renders "
        "immediately — no persistence, no waiting for the autonomous "
        "recompute pipeline. Same evaluator path as the recompute service "
        "so the preview value matches what eventually lands in the DB."
    ),
    dependencies=[Depends(RequirePermission(codename="pricing:read"))],
)
async def preview_sku_pricing(
    body: PreviewSkuPricingRequest,
    handler: FromDishka[PreviewSkuPricingHandler],
    is_admin: bool = Depends(_caller_is_pricing_admin),
) -> PreviewSkuPricingResponse:
    result = await handler.handle(
        PreviewSkuPricingQuery(
            product_id=body.product_id,
            category_id=body.category_id,
            context_id=body.context_id,
            purchase_price_amount=body.purchase_price.amount,
            purchase_currency=body.purchase_price.currency,
            supplier_id=body.supplier_id,
        )
    )
    components = result.components if is_admin else {}
    bindings = (
        [FormulaBindingValue.model_validate(b) for b in result.bindings]
        if is_admin
        else []
    )
    return PreviewSkuPricingResponse(
        final_price=result.final_price,
        components=components,
        bindings=bindings,
        formula_version_id=result.formula_version_id,
        formula_version_number=result.formula_version_number,
        context_id=result.context_id,
    )
