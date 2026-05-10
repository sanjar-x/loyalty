"""FastAPI router for ProductVariant CRUD endpoints."""

import uuid

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Depends, Query, Response, status

from src.api.dependencies.etag import attach_etag, parse_if_match
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
from src.modules.catalog.domain.value_objects import Money
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
from src.shared.exceptions import OptimisticLockError, PreconditionFailedError

variant_router = APIRouter(
    prefix="/admin/catalog/products/{product_id}/variants",
    tags=["Admin / Catalog / Variants"],
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
    default_price_money: Money | None = None
    if request.default_price is not None:
        default_price_money = Money(
            amount=request.default_price.amount,
            currency=request.default_price.currency,
        )
    command = AddVariantCommand(
        product_id=product_id,
        name_i18n=request.name_i18n,
        description_i18n=request.description_i18n,
        sort_order=request.sort_order,
        default_price=default_price_money,
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
    response: Response,
    handler: FromDishka[ListVariantsHandler],
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> ProductVariantListResponse:
    """Return paginated active variants for the given product."""
    response.headers["Cache-Control"] = "no-store"
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
    response: Response,
    handler: FromDishka[UpdateVariantHandler],
    if_match_version: int | None = Depends(parse_if_match),
) -> ProductVariantUpdateResponse:
    """Partially update a product variant.

    T-1.3 — accepts ``If-Match: "v{N}"``. Mismatch → 412
    ``PRECONDITION_FAILED``. Header absent → legacy last-write-wins.
    """
    command = build_update_command(
        request,
        UpdateVariantCommand,
        field_converters={
            "default_price": lambda schema: (
                Money(amount=schema.amount, currency=schema.currency)
                if schema is not None
                else None
            ),
        },
        product_id=product_id,
        variant_id=variant_id,
        expected_version=if_match_version,
    )
    try:
        result = await handler.handle(command)
    except OptimisticLockError as exc:
        if if_match_version is not None:
            raise PreconditionFailedError(
                entity_type="ProductVariant",
                entity_id=variant_id,
                expected_version=if_match_version,
                current_version=exc.details.get("actual_version"),
            ) from exc
        raise
    attach_etag(response, result.version)
    return ProductVariantUpdateResponse(
        id=result.id, message="Variant updated", version=result.version
    )


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
