"""
FastAPI router for SKU (variant) CRUD endpoints.

All mutating endpoints require the ``catalog:manage`` permission.
Delegates to application-layer command/query handlers via Dishka DI.
"""

import uuid

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Depends, status

from src.modules.catalog.application.commands.add_sku import (
    AddSKUCommand,
    AddSKUHandler,
)
from src.modules.catalog.application.commands.delete_sku import (
    DeleteSKUCommand,
    DeleteSKUHandler,
)
from src.modules.catalog.application.commands.update_sku import (
    UpdateSKUCommand,
    UpdateSKUHandler,
)
from src.modules.catalog.application.queries.list_skus import (
    ListSKUsHandler,
    ListSKUsQuery,
)
from src.modules.catalog.presentation.mappers import to_sku_response
from src.modules.catalog.presentation.schemas import (
    SKUCreateRequest,
    SKUCreateResponse,
    SKUResponse,
    SKUUpdateRequest,
)
from src.modules.identity.presentation.dependencies import RequirePermission

sku_router = APIRouter(
    prefix="/products/{product_id}/skus",
    tags=["SKUs"],
    route_class=DishkaRoute,
)


@sku_router.post(
    path="",
    status_code=status.HTTP_201_CREATED,
    response_model=SKUCreateResponse,
    summary="Add a SKU variant to a product",
    description="Create a new SKU variant with price and attributes.",
    dependencies=[Depends(RequirePermission(codename="catalog:manage"))],
)
async def create_sku(
    product_id: uuid.UUID,
    request: SKUCreateRequest,
    handler: FromDishka[AddSKUHandler],
) -> SKUCreateResponse:
    """Create a new SKU variant for the given product."""
    command = AddSKUCommand(
        product_id=product_id,
        sku_code=request.sku_code,
        price_amount=request.price_amount,
        price_currency=request.price_currency,
        compare_at_price_amount=request.compare_at_price_amount,
        is_active=request.is_active,
        variant_attributes=[
            (pair.attribute_id, pair.attribute_value_id)
            for pair in request.variant_attributes
        ],
    )
    result = await handler.handle(command)
    return SKUCreateResponse(id=result.sku_id, message="SKU created")


@sku_router.get(
    path="",
    status_code=status.HTTP_200_OK,
    response_model=list[SKUResponse],
    summary="List SKU variants for a product",
    description="Return all SKU variants belonging to the given product.",
)
async def list_skus(
    product_id: uuid.UUID,
    handler: FromDishka[ListSKUsHandler],
) -> list[SKUResponse]:
    """Return all SKU variants belonging to the given product."""
    query = ListSKUsQuery(product_id=product_id)
    results = await handler.handle(query)
    return [to_sku_response(model) for model in results]


@sku_router.patch(
    path="/{sku_id}",
    status_code=status.HTTP_200_OK,
    response_model=SKUResponse,
    summary="Update a SKU variant",
    description="Partially update a SKU variant. Only provided fields change.",
    dependencies=[Depends(RequirePermission(codename="catalog:manage"))],
)
async def update_sku(
    product_id: uuid.UUID,
    sku_id: uuid.UUID,
    request: SKUUpdateRequest,
    update_handler: FromDishka[UpdateSKUHandler],
    list_handler: FromDishka[ListSKUsHandler],
) -> SKUResponse:
    """Apply a partial update to a SKU variant and return the updated state."""
    # Build command kwargs; only pass compare_at_price_amount when the client
    # actually provided a value (distinguishing "not sent" from "explicitly null").
    cmd_kwargs: dict[str, object] = {
        "product_id": product_id,
        "sku_id": sku_id,
        "sku_code": request.sku_code,
        "price_amount": request.price_amount,
        "price_currency": request.price_currency,
        "is_active": request.is_active,
        "version": request.version,
    }

    # Sentinel handling: Pydantic uses `...` (Ellipsis) as default.
    # Only forward compare_at_price_amount when the client explicitly sent it.
    if request.compare_at_price_amount is not ...:
        cmd_kwargs["compare_at_price_amount"] = request.compare_at_price_amount

    # Only forward variant_attributes when the client explicitly sent them.
    if request.variant_attributes is not None:
        cmd_kwargs["variant_attributes"] = [
            (p.attribute_id, p.attribute_value_id) for p in request.variant_attributes
        ]

    command = UpdateSKUCommand(**cmd_kwargs)  # type: ignore[arg-type]
    result = await update_handler.handle(command)

    # Fetch updated SKU list and find the one we just updated.
    updated_skus = await list_handler.handle(ListSKUsQuery(product_id=product_id))
    updated_sku = next(s for s in updated_skus if s.id == result.id)
    return to_sku_response(updated_sku)


@sku_router.delete(
    path="/{sku_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete a SKU variant",
    description="Soft-delete a SKU variant from the product.",
    dependencies=[Depends(RequirePermission(codename="catalog:manage"))],
)
async def delete_sku(
    product_id: uuid.UUID,
    sku_id: uuid.UUID,
    handler: FromDishka[DeleteSKUHandler],
) -> None:
    """Soft-delete a SKU variant from the product."""
    command = DeleteSKUCommand(product_id=product_id, sku_id=sku_id)
    await handler.handle(command)

