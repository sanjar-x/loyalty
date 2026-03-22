"""FastAPI router for ProductVariant CRUD endpoints."""

import uuid

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Depends, status

from src.modules.catalog.application.commands.add_variant import (
    AddVariantCommand,
    AddVariantHandler,
)
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
from src.modules.catalog.presentation.mappers import to_sku_response
from src.modules.catalog.presentation.schemas import (
    MoneySchema,
    ProductVariantCreateRequest,
    ProductVariantResponse,
    ProductVariantUpdateRequest,
    SKUResponse,
)
from src.modules.identity.presentation.dependencies import RequirePermission

variant_router = APIRouter(
    prefix="/products/{product_id}/variants",
    tags=["Product Variants"],
    route_class=DishkaRoute,
)


def _to_variant_response(v) -> ProductVariantResponse:  # noqa: ANN001
    """Convert a ProductVariantReadModel to a ProductVariantResponse schema."""
    return ProductVariantResponse(
        id=v.id,
        name_i18n=v.name_i18n,
        description_i18n=v.description_i18n,
        sort_order=v.sort_order,
        default_price=MoneySchema(
            amount=v.default_price.amount, currency=v.default_price.currency
        )
        if v.default_price
        else None,
        skus=[to_sku_response(s) for s in v.skus],
    )


@variant_router.post(
    path="",
    status_code=status.HTTP_201_CREATED,
    summary="Create a product variant",
    dependencies=[Depends(RequirePermission(codename="catalog:manage"))],
)
async def create_variant(
    product_id: uuid.UUID,
    request: ProductVariantCreateRequest,
    handler: FromDishka[AddVariantHandler],
):
    """Create a new variant for the given product."""
    command = AddVariantCommand(
        product_id=product_id,
        name_i18n=request.name_i18n,
        description_i18n=request.description_i18n,
        sort_order=request.sort_order,
        default_price_amount=request.default_price_amount,
        default_price_currency=request.default_price_currency,
    )
    result = await handler.handle(command)
    return {"id": result.variant_id, "message": "Variant created"}


@variant_router.get(
    path="",
    status_code=status.HTTP_200_OK,
    response_model=list[ProductVariantResponse],
    summary="List product variants",
)
async def list_variants(
    product_id: uuid.UUID,
    handler: FromDishka[ListVariantsHandler],
):
    """Return all active variants for the given product."""
    query = ListVariantsQuery(product_id=product_id)
    results = await handler.handle(query)
    return [_to_variant_response(v) for v in results]


@variant_router.patch(
    path="/{variant_id}",
    status_code=status.HTTP_200_OK,
    summary="Update a product variant",
    dependencies=[Depends(RequirePermission(codename="catalog:manage"))],
)
async def update_variant(
    product_id: uuid.UUID,
    variant_id: uuid.UUID,
    request: ProductVariantUpdateRequest,
    handler: FromDishka[UpdateVariantHandler],
):
    """Partially update a product variant. Only provided fields are modified."""
    provided_fields = request.model_fields_set
    cmd_kwargs: dict[str, object] = {
        "product_id": product_id,
        "variant_id": variant_id,
        "_provided_fields": frozenset(provided_fields),
    }
    for field_name in provided_fields:
        cmd_kwargs[field_name] = getattr(request, field_name)
    command = UpdateVariantCommand(**cmd_kwargs)  # type: ignore[arg-type]
    result = await handler.handle(command)
    return {"id": result.id, "message": "Variant updated"}


@variant_router.delete(
    path="/{variant_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a product variant",
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
