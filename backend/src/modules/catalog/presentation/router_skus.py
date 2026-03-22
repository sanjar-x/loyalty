"""
FastAPI router for SKU CRUD endpoints.

Nested under ``/catalog/products/{product_id}/variants/{variant_id}/skus``.
All mutating endpoints require the ``catalog:manage`` permission.
Delegates to application-layer command/query handlers via Dishka DI.
"""

import uuid

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Depends, Query, status

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
from src.modules.catalog.domain.exceptions import SKUNotFoundError
from src.modules.catalog.presentation.mappers import to_sku_response
from src.modules.catalog.presentation.schemas import (
    SKUCreateRequest,
    SKUCreateResponse,
    SKUListResponse,
    SKUResponse,
    SKUUpdateRequest,
)
from src.modules.catalog.presentation.update_helpers import build_update_command
from src.modules.identity.presentation.dependencies import RequirePermission

sku_router = APIRouter(
    prefix="/products/{product_id}/variants/{variant_id}/skus",
    tags=["SKUs"],
    route_class=DishkaRoute,
)


@sku_router.post(
    path="",
    status_code=status.HTTP_201_CREATED,
    response_model=SKUCreateResponse,
    summary="Add a SKU to a variant",
    description="Create a new SKU with optional price and attributes.",
    dependencies=[Depends(RequirePermission(codename="catalog:manage"))],
)
async def create_sku(
    product_id: uuid.UUID,
    variant_id: uuid.UUID,
    request: SKUCreateRequest,
    handler: FromDishka[AddSKUHandler],
) -> SKUCreateResponse:
    """Create a new SKU for the given product variant."""
    command = AddSKUCommand(
        product_id=product_id,
        variant_id=variant_id,
        sku_code=request.sku_code,
        price_amount=request.price_amount,
        price_currency=request.price_currency,
        compare_at_price_amount=request.compare_at_price_amount,
        is_active=request.is_active,
        variant_attributes=[
            (pair.attribute_id, pair.attribute_value_id) for pair in request.variant_attributes
        ],
    )
    result = await handler.handle(command)
    return SKUCreateResponse(id=result.sku_id, message="SKU created")


@sku_router.get(
    path="",
    status_code=status.HTTP_200_OK,
    response_model=SKUListResponse,
    summary="List SKUs for a variant",
    description="Return paginated SKUs belonging to the given product variant.",
)
async def list_skus(
    product_id: uuid.UUID,
    variant_id: uuid.UUID,
    handler: FromDishka[ListSKUsHandler],
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> SKUListResponse:
    """Return paginated SKUs belonging to the given product."""
    query = ListSKUsQuery(product_id=product_id, variant_id=variant_id, offset=offset, limit=limit)
    items, total = await handler.handle(query)
    return SKUListResponse(
        items=[to_sku_response(model) for model in items],
        total=total,
        offset=offset,
        limit=limit,
    )


@sku_router.patch(
    path="/{sku_id}",
    status_code=status.HTTP_200_OK,
    response_model=SKUResponse,
    summary="Update a SKU",
    description="Partially update a SKU. Only provided fields change.",
    dependencies=[Depends(RequirePermission(codename="catalog:manage"))],
)
async def update_sku(
    product_id: uuid.UUID,
    variant_id: uuid.UUID,
    sku_id: uuid.UUID,
    request: SKUUpdateRequest,
    update_handler: FromDishka[UpdateSKUHandler],
    list_handler: FromDishka[ListSKUsHandler],
) -> SKUResponse:
    """Apply a partial update to a SKU and return the updated state."""
    command = build_update_command(
        request,
        UpdateSKUCommand,
        exclude_from_provided=frozenset({"version"}),
        field_converters={
            "variant_attributes": lambda pairs: [
                (p.attribute_id, p.attribute_value_id) for p in pairs
            ],
        },
        product_id=product_id,
        sku_id=sku_id,
        version=request.version,
    )
    result = await update_handler.handle(command)

    # Fetch updated SKU list scoped to the variant and find the one we updated.
    updated_skus, _ = await list_handler.handle(
        ListSKUsQuery(product_id=product_id, variant_id=variant_id, limit=None)
    )
    updated_sku = next((s for s in updated_skus if s.id == result.id), None)
    if updated_sku is None:
        raise SKUNotFoundError(sku_id=result.id)
    return to_sku_response(updated_sku)


@sku_router.delete(
    path="/{sku_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete a SKU",
    description="Soft-delete a SKU from the product variant.",
    dependencies=[Depends(RequirePermission(codename="catalog:manage"))],
)
async def delete_sku(
    product_id: uuid.UUID,
    variant_id: uuid.UUID,
    sku_id: uuid.UUID,
    handler: FromDishka[DeleteSKUHandler],
) -> None:
    """Soft-delete a SKU from the product variant.

    Note: variant_id is present in the URL for hierarchical consistency but
    is not validated against the SKU. The DeleteSKUCommand only uses
    product_id + sku_id; the domain layer verifies SKU ownership via the
    product aggregate.
    """
    command = DeleteSKUCommand(product_id=product_id, sku_id=sku_id)
    await handler.handle(command)
