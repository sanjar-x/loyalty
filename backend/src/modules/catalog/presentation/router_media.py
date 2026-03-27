"""
FastAPI router for Product media asset endpoints.

Nested under ``/catalog/products/{product_id}/media``.
All mutating endpoints require the ``catalog:manage`` permission.
Delegates to application-layer command/query handlers via Dishka DI.
"""

import uuid

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Depends, Query, Response, status

from src.modules.catalog.application.commands.add_product_media import (
    AddProductMediaCommand,
    AddProductMediaHandler,
    AddProductMediaResult,
)
from src.modules.catalog.application.commands.delete_product_media import (
    DeleteProductMediaCommand,
    DeleteProductMediaHandler,
)
from src.modules.catalog.application.commands.reorder_product_media import (
    ReorderItem,
    ReorderProductMediaCommand,
    ReorderProductMediaHandler,
)
from src.modules.catalog.application.commands.update_product_media import (
    UpdateProductMediaCommand,
    UpdateProductMediaHandler,
    UpdateProductMediaResult,
)
from src.modules.catalog.application.queries.list_product_media import (
    ListProductMediaHandler,
    ListProductMediaQuery,
)
from src.modules.catalog.presentation.schemas import (
    MediaAssetCreateRequest,
    MediaAssetCreateResponse,
    MediaAssetListResponse,
    MediaAssetReorderRequest,
    MediaAssetResponse,
    MediaAssetUpdateRequest,
    MediaAssetUpdateResponse,
)
from src.modules.catalog.presentation.update_helpers import build_update_command
from src.modules.identity.presentation.dependencies import RequirePermission

media_router = APIRouter(
    prefix="/products/{product_id}/media",
    tags=["Product Media"],
    route_class=DishkaRoute,
)


@media_router.post(
    path="",
    status_code=status.HTTP_201_CREATED,
    response_model=MediaAssetCreateResponse,
    summary="Add a media asset to a product",
    description=(
        "Create a new media asset record linking a storage object "
        "(from ImageBackend) or external URL to the product."
    ),
    dependencies=[Depends(RequirePermission(codename="catalog:manage"))],
)
async def add_product_media(
    product_id: uuid.UUID,
    request: MediaAssetCreateRequest,
    handler: FromDishka[AddProductMediaHandler],
) -> MediaAssetCreateResponse:
    """Add a media asset to a product."""
    command = AddProductMediaCommand(
        product_id=product_id,
        storage_object_id=request.storage_object_id,
        variant_id=request.variant_id,
        media_type=request.media_type,
        role=request.role,
        sort_order=request.sort_order,
        is_external=request.is_external,
        url=request.url,
    )
    result: AddProductMediaResult = await handler.handle(command)
    return MediaAssetCreateResponse(id=result.media_id, message="Media asset created")


@media_router.get(
    path="",
    status_code=status.HTTP_200_OK,
    response_model=MediaAssetListResponse,
    summary="List media assets for a product",
    description="Return paginated media assets ordered by variant and sort_order.",
    dependencies=[Depends(RequirePermission(codename="catalog:read"))],
)
async def list_product_media(
    product_id: uuid.UUID,
    response: Response,
    handler: FromDishka[ListProductMediaHandler],
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
) -> MediaAssetListResponse:
    """List media assets for a product."""
    response.headers["Cache-Control"] = "no-store"
    query = ListProductMediaQuery(product_id=product_id, offset=offset, limit=limit)
    result = await handler.handle(query)
    return MediaAssetListResponse(
        items=[
            MediaAssetResponse(
                id=item.id,
                product_id=item.product_id,
                variant_id=item.variant_id,
                media_type=item.media_type,
                role=item.role,
                sort_order=item.sort_order,
                storage_object_id=item.storage_object_id,
                url=item.url,
                is_external=item.is_external,
                image_variants=item.image_variants,
                created_at=item.created_at,
                updated_at=item.updated_at,
            )
            for item in result.items
        ],
        total=result.total,
        offset=result.offset,
        limit=result.limit,
    )


@media_router.patch(
    path="/{media_id}",
    status_code=status.HTTP_200_OK,
    response_model=MediaAssetUpdateResponse,
    summary="Update a media asset",
    description="Partially update a media asset's role, variant binding, or sort order.",
    dependencies=[Depends(RequirePermission(codename="catalog:manage"))],
)
async def update_product_media(
    product_id: uuid.UUID,
    media_id: uuid.UUID,
    request: MediaAssetUpdateRequest,
    handler: FromDishka[UpdateProductMediaHandler],
) -> MediaAssetUpdateResponse:
    """Partially update a media asset."""
    command = build_update_command(
        request,
        UpdateProductMediaCommand,
        product_id=product_id,
        media_id=media_id,
    )
    result: UpdateProductMediaResult = await handler.handle(command)
    return MediaAssetUpdateResponse(id=result.id, message="Media asset updated")


@media_router.delete(
    path="/{media_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a media asset",
    description="Delete a media asset and trigger best-effort ImageBackend cleanup.",
    dependencies=[Depends(RequirePermission(codename="catalog:manage"))],
)
async def delete_product_media(
    product_id: uuid.UUID,
    media_id: uuid.UUID,
    handler: FromDishka[DeleteProductMediaHandler],
) -> None:
    """Delete a media asset from a product."""
    command = DeleteProductMediaCommand(product_id=product_id, media_id=media_id)
    await handler.handle(command)


@media_router.post(
    path="/reorder",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Reorder media assets",
    description="Bulk-update sort_order for media assets belonging to this product.",
    dependencies=[Depends(RequirePermission(codename="catalog:manage"))],
)
async def reorder_product_media(
    product_id: uuid.UUID,
    request: MediaAssetReorderRequest,
    handler: FromDishka[ReorderProductMediaHandler],
) -> None:
    """Bulk-reorder media assets for a product."""
    command = ReorderProductMediaCommand(
        product_id=product_id,
        items=[
            ReorderItem(media_id=item.media_id, sort_order=item.sort_order)
            for item in request.items
        ],
    )
    await handler.handle(command)
