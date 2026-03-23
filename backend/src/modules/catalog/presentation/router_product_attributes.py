"""
FastAPI router for Product attribute assignment endpoints.

Nested under ``/catalog/products/{product_id}/attributes``.
All mutating endpoints require the ``catalog:manage`` permission.
Delegates to application-layer command/query handlers via Dishka DI.
"""

import uuid

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Depends, Query, status

from src.modules.catalog.application.commands.assign_product_attribute import (
    AssignProductAttributeCommand,
    AssignProductAttributeHandler,
    AssignProductAttributeResult,
)
from src.modules.catalog.application.commands.delete_product_attribute import (
    DeleteProductAttributeCommand,
    DeleteProductAttributeHandler,
)
from src.modules.catalog.application.queries.list_product_attributes import (
    ListProductAttributesHandler,
    ListProductAttributesQuery,
)
from src.modules.catalog.presentation.schemas import (
    ProductAttributeAssignRequest,
    ProductAttributeAssignResponse,
    ProductAttributeListResponse,
    ProductAttributeResponse,
)
from src.modules.identity.presentation.dependencies import RequirePermission

product_attribute_router = APIRouter(
    prefix="/products/{product_id}/attributes",
    tags=["Product Attributes"],
    route_class=DishkaRoute,
)


@product_attribute_router.post(
    path="",
    status_code=status.HTTP_201_CREATED,
    response_model=ProductAttributeAssignResponse,
    summary="Assign an attribute value to a product",
    description="Assign a specific attribute value to the given product.",
    dependencies=[Depends(RequirePermission(codename="catalog:manage"))],
)
async def assign_product_attribute(
    product_id: uuid.UUID,
    request: ProductAttributeAssignRequest,
    handler: FromDishka[AssignProductAttributeHandler],
) -> ProductAttributeAssignResponse:
    """Assign an attribute value to a product.

    Args:
        product_id: UUID of the target product.
        request: Attribute assignment payload.
        handler: Injected command handler.

    Returns:
        Response with the new assignment ID.
    """
    command = AssignProductAttributeCommand(
        product_id=product_id,
        attribute_id=request.attribute_id,
        attribute_value_id=request.attribute_value_id,
    )
    result: AssignProductAttributeResult = await handler.handle(command)
    return ProductAttributeAssignResponse(id=result.pav_id, message="Attribute assigned to product")


@product_attribute_router.get(
    path="",
    status_code=status.HTTP_200_OK,
    response_model=ProductAttributeListResponse,
    summary="List attribute assignments for a product",
    description="Return paginated attribute value assignments for a product.",
    dependencies=[Depends(RequirePermission(codename="catalog:read"))],
)
async def list_product_attributes(
    product_id: uuid.UUID,
    handler: FromDishka[ListProductAttributesHandler],
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> ProductAttributeListResponse:
    """List all attribute value assignments for a product.

    Args:
        product_id: UUID of the target product.
        handler: Injected query handler.
        limit: Maximum number of items to return.
        offset: Number of items to skip.

    Returns:
        Paginated product attribute assignment responses.
    """
    query = ListProductAttributesQuery(product_id=product_id, offset=offset, limit=limit)
    result = await handler.handle(query)
    return ProductAttributeListResponse(
        items=[
            ProductAttributeResponse(
                id=item.id,
                product_id=item.product_id,
                attribute_id=item.attribute_id,
                attribute_value_id=item.attribute_value_id,
                attribute_code=item.attribute_code,
                attribute_name_i18n=item.attribute_name_i18n,
            )
            for item in result.items
        ],
        total=result.total,
        offset=result.offset,
        limit=result.limit,
    )


@product_attribute_router.delete(
    path="/{attribute_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an attribute assignment from a product",
    description="Un-assign an attribute from the given product.",
    dependencies=[Depends(RequirePermission(codename="catalog:manage"))],
)
async def delete_product_attribute(
    product_id: uuid.UUID,
    attribute_id: uuid.UUID,
    handler: FromDishka[DeleteProductAttributeHandler],
) -> None:
    """Delete an attribute assignment from a product.

    Args:
        product_id: UUID of the target product.
        attribute_id: UUID of the attribute to un-assign.
        handler: Injected command handler.
    """
    command = DeleteProductAttributeCommand(
        product_id=product_id,
        attribute_id=attribute_id,
    )
    await handler.handle(command)
