"""
FastAPI router for SKU CRUD endpoints.

Nested under ``/catalog/products/{product_id}/variants/{variant_id}/skus``.
All mutating endpoints require the ``catalog:manage`` permission.
Delegates to application-layer command/query handlers via Dishka DI.
"""

import uuid
from typing import Annotated

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Depends, Path, Query, Response, status

from src.api.dependencies.etag import attach_etag, parse_if_match
from src.modules.catalog.application.commands.add_sku import (
    AddSKUCommand,
    AddSKUHandler,
)
from src.modules.catalog.application.commands.delete_sku import (
    DeleteSKUCommand,
    DeleteSKUHandler,
)
from src.modules.catalog.application.commands.generate_sku_matrix import (
    AttributeSelection,
    GenerateSKUMatrixCommand,
    GenerateSKUMatrixHandler,
)
from src.modules.catalog.application.commands.update_sku import (
    UpdateSKUCommand,
    UpdateSKUHandler,
)
from src.modules.catalog.application.queries.list_skus import (
    ListSKUsHandler,
    ListSKUsQuery,
)
from src.modules.catalog.domain.exceptions import ConcurrencyError, SKUNotFoundError
from src.modules.catalog.domain.value_objects import Money
from src.modules.catalog.presentation.mappers import to_sku_response
from src.modules.catalog.presentation.schemas import (
    MoneySchema,
    SKUCreateRequest,
    SKUCreateResponse,
    SKUListResponse,
    SKUMatrixGenerateRequest,
    SKUMatrixGenerateResponse,
    SKUResponse,
    SKUUpdateRequest,
)
from src.modules.catalog.presentation.update_helpers import build_update_command
from src.modules.identity.presentation.dependencies import RequirePermission
from src.shared.exceptions import OptimisticLockError, PreconditionFailedError


def _money_from_schema(schema: MoneySchema | None) -> Money | None:
    """Convert presentation ``MoneySchema`` to domain ``Money`` value object."""
    if schema is None:
        return None
    return Money(amount=schema.amount, currency=schema.currency)


sku_router = APIRouter(
    prefix="/admin/catalog/products/{productId}/variants/{variantId}/skus",
    tags=["Admin / Catalog / SKUs"],
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
async def add_sku(
    product_id: Annotated[uuid.UUID, Path(alias="productId")],
    variant_id: Annotated[uuid.UUID, Path(alias="variantId")],
    request: SKUCreateRequest,
    handler: FromDishka[AddSKUHandler],
) -> SKUCreateResponse:
    """Create a new SKU for the given product variant."""
    command = AddSKUCommand(
        product_id=product_id,
        variant_id=variant_id,
        sku_code=request.sku_code,
        price=_money_from_schema(request.price),
        compare_at_price=_money_from_schema(request.compare_at_price),
        purchase_price=_money_from_schema(request.purchase_price),
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
    response_model=SKUListResponse,
    summary="List SKUs for a variant",
    description="Return paginated SKUs belonging to the given product variant.",
    dependencies=[Depends(RequirePermission(codename="catalog:read"))],
)
async def list_skus(
    product_id: Annotated[uuid.UUID, Path(alias="productId")],
    variant_id: Annotated[uuid.UUID, Path(alias="variantId")],
    response: Response,
    handler: FromDishka[ListSKUsHandler],
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> SKUListResponse:
    """Return paginated SKUs belonging to the given product."""
    response.headers["Cache-Control"] = "no-store"
    query = ListSKUsQuery(
        product_id=product_id, variant_id=variant_id, offset=offset, limit=limit
    )
    result = await handler.handle(query)
    return SKUListResponse(
        items=[to_sku_response(model) for model in result.items],
        total=result.total,
        offset=result.offset,
        limit=result.limit,
    )


@sku_router.post(
    path="/generate",
    status_code=status.HTTP_201_CREATED,
    response_model=SKUMatrixGenerateResponse,
    summary="Generate SKU matrix from attribute selections",
    description=(
        "Generates all SKU combinations from the cartesian product of "
        "attribute selections. Existing combinations are skipped. "
        "All SKUs are created in a single transaction."
    ),
    dependencies=[Depends(RequirePermission(codename="catalog:manage"))],
)
async def generate_sku_matrix(
    product_id: Annotated[uuid.UUID, Path(alias="productId")],
    variant_id: Annotated[uuid.UUID, Path(alias="variantId")],
    request: SKUMatrixGenerateRequest,
    handler: FromDishka[GenerateSKUMatrixHandler],
) -> SKUMatrixGenerateResponse:
    """Generate SKU combinations from attribute selections."""
    command = GenerateSKUMatrixCommand(
        product_id=product_id,
        variant_id=variant_id,
        attribute_selections=[
            AttributeSelection(
                attribute_id=sel.attribute_id,
                value_ids=list(sel.value_ids),
            )
            for sel in request.attribute_selections
        ],
        price=_money_from_schema(request.price),
        compare_at_price=_money_from_schema(request.compare_at_price),
        is_active=request.is_active,
    )
    result = await handler.handle(command)
    return SKUMatrixGenerateResponse(
        created_count=result.created_count,
        skipped_count=result.skipped_count,
        sku_ids=result.sku_ids,
        message=f"Generated {result.created_count} SKUs, skipped {result.skipped_count} existing",
    )


@sku_router.patch(
    path="/{skuId}",
    status_code=status.HTTP_200_OK,
    response_model=SKUResponse,
    summary="Update a SKU",
    description="Partially update a SKU. Only provided fields change.",
    dependencies=[Depends(RequirePermission(codename="catalog:manage"))],
)
async def update_sku(
    product_id: Annotated[uuid.UUID, Path(alias="productId")],
    variant_id: Annotated[uuid.UUID, Path(alias="variantId")],
    sku_id: Annotated[uuid.UUID, Path(alias="skuId")],
    request: SKUUpdateRequest,
    response: Response,
    update_handler: FromDishka[UpdateSKUHandler],
    list_handler: FromDishka[ListSKUsHandler],
    if_match_version: int | None = Depends(parse_if_match),
) -> SKUResponse:
    """Apply a partial update to a SKU and return the updated state.

    T-1.4 — accepts ``If-Match: "v{N}"``. Mismatch → 412
    ``PRECONDITION_FAILED``. Header absent → legacy body-level
    ``version`` field continues to enforce optimistic locking with
    409 ``CONCURRENCY_ERROR`` (kept for backwards compatibility).
    """
    command = build_update_command(
        request,
        UpdateSKUCommand,
        exclude_from_provided=frozenset({"version"}),
        field_converters={
            "variant_attributes": lambda pairs: [
                (p.attribute_id, p.attribute_value_id) for p in pairs
            ],
            "price": _money_from_schema,
            "compare_at_price": _money_from_schema,
            "purchase_price": _money_from_schema,
        },
        product_id=product_id,
        sku_id=sku_id,
        version=request.version,
        expected_version=if_match_version,
    )
    # The handler already validates that the SKU belongs to the product
    # (raises SKUNotFoundError if not found within the aggregate).
    try:
        result = await update_handler.handle(command)
    except OptimisticLockError as exc:
        # Only the header-driven path upgrades to 412; legacy body
        # version mismatches keep their existing 409 ``ConcurrencyError``
        # surface (which itself extends OptimisticLockError but is
        # raised separately, hence the ``isinstance`` narrowing).
        if if_match_version is not None and not isinstance(exc, ConcurrencyError):
            raise PreconditionFailedError(
                entity_type="SKU",
                entity_id=sku_id,
                expected_version=if_match_version,
                current_version=exc.details.get("actual_version"),
            ) from exc
        raise
    attach_etag(response, result.version)

    # Fetch updated SKU read model scoped to the variant.
    sku_list = await list_handler.handle(
        ListSKUsQuery(product_id=product_id, variant_id=variant_id, limit=None)
    )
    updated_sku = next((s for s in sku_list.items if s.id == result.id), None)
    if updated_sku is None:
        raise SKUNotFoundError(sku_id=result.id)
    return to_sku_response(updated_sku)


@sku_router.delete(
    path="/{skuId}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete a SKU",
    description="Soft-delete a SKU from the product variant.",
    dependencies=[Depends(RequirePermission(codename="catalog:manage"))],
)
async def delete_sku(
    product_id: Annotated[uuid.UUID, Path(alias="productId")],
    variant_id: Annotated[uuid.UUID, Path(alias="variantId")],
    sku_id: Annotated[uuid.UUID, Path(alias="skuId")],
    handler: FromDishka[DeleteSKUHandler],
) -> None:
    """Soft-delete a SKU from the product variant.

    The handler fetches the product aggregate and calls
    ``Product.remove_sku()``, which raises ``SKUNotFoundError`` if the
    SKU does not belong to the product -- no separate IDOR pre-check needed.
    """
    command = DeleteSKUCommand(product_id=product_id, sku_id=sku_id)
    await handler.handle(command)
