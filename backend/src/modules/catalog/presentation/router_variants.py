"""FastAPI router for ProductVariant CRUD endpoints."""

import uuid

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Depends, Query, status

from src.modules.catalog.application.commands.add_variant import (
    AddVariantCommand,
    AddVariantHandler,
)
from src.modules.catalog.domain.value_objects import DEFAULT_CURRENCY
from src.modules.catalog.application.commands.delete_variant import (
    DeleteVariantCommand,
    DeleteVariantHandler,
)
from src.modules.catalog.application.commands.update_variant import (
    UpdateVariantCommand,
    UpdateVariantHandler,
)
from src.modules.catalog.application.queries.list_variants import (
    ListVariantsHandler,
    ListVariantsQuery,
)
from src.modules.catalog.presentation.mappers import to_variant_response
from src.modules.catalog.presentation.schemas import (
    ProductVariantCreateRequest,
    ProductVariantCreateResponse,
    ProductVariantListResponse,
    ProductVariantUpdateRequest,
    ProductVariantUpdateResponse,
)
from src.modules.catalog.presentation.update_helpers import build_update_command
from src.modules.identity.presentation.dependencies import RequirePermission

variant_router = APIRouter(
    prefix="/products/{product_id}/variants",
    tags=["Product Variants"],
    route_class=DishkaRoute,
)


@variant_router.post(
    path="",
    status_code=status.HTTP_201_CREATED,
    response_model=ProductVariantCreateResponse,
    summary="Create a product variant",
    description="Create a new variant for the given product.",
    dependencies=[Depends(RequirePermission(codename="catalog:manage"))],
)
async def add_variant(
    product_id: uuid.UUID,
    request: ProductVariantCreateRequest,
    handler: FromDishka[AddVariantHandler],
) -> ProductVariantCreateResponse:
    """Create a new variant for the given product."""
    command = AddVariantCommand(
        product_id=product_id,
        name_i18n=request.name_i18n,
        description_i18n=request.description_i18n,
        sort_order=request.sort_order,
        default_price_amount=request.default_price_amount,
        default_price_currency=request.default_price_currency or DEFAULT_CURRENCY,
    )
    result = await handler.handle(command)
    return ProductVariantCreateResponse(id=result.variant_id, message="Variant created")


@variant_router.get(
    path="",
    status_code=status.HTTP_200_OK,
    response_model=ProductVariantListResponse,
    summary="List product variants",
    description="Return paginated active variants for the given product.",
    dependencies=[Depends(RequirePermission(codename="catalog:read"))],
)
async def list_variants(
    product_id: uuid.UUID,
    handler: FromDishka[ListVariantsHandler],
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> ProductVariantListResponse:
    """Return paginated active variants for the given product."""
    query = ListVariantsQuery(product_id=product_id, offset=offset, limit=limit)
    result = await handler.handle(query)
    return ProductVariantListResponse(
        items=[to_variant_response(v) for v in result.items],
        total=result.total,
        offset=result.offset,
        limit=result.limit,
    )


@variant_router.patch(
    path="/{variant_id}",
    status_code=status.HTTP_200_OK,
    response_model=ProductVariantUpdateResponse,
    summary="Update a product variant",
    description="Partially update a product variant. Only provided fields are modified.",
    dependencies=[Depends(RequirePermission(codename="catalog:manage"))],
)
async def update_variant(
    product_id: uuid.UUID,
    variant_id: uuid.UUID,
    request: ProductVariantUpdateRequest,
    handler: FromDishka[UpdateVariantHandler],
) -> ProductVariantUpdateResponse:
    """Partially update a product variant. Only provided fields are modified."""
    command = build_update_command(
        request,
        UpdateVariantCommand,
        product_id=product_id,
        variant_id=variant_id,
    )
    result = await handler.handle(command)
    return ProductVariantUpdateResponse(id=result.id, message="Variant updated")


@variant_router.delete(
    path="/{variant_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a product variant",
    description="Soft-delete a product variant from the product.",
    dependencies=[Depends(RequirePermission(codename="catalog:manage"))],
)
async def delete_variant(
    product_id: uuid.UUID,
    variant_id: uuid.UUID,
    handler: FromDishka[DeleteVariantHandler],
) -> None:
    """Soft-delete a product variant from the product."""
    command = DeleteVariantCommand(product_id=product_id, variant_id=variant_id)
    await handler.handle(command)
