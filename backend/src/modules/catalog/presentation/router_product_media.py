"""
FastAPI router for product media asset management endpoints.

Nested under ``/catalog/products/{product_id}/media``.
All mutating endpoints require the ``catalog:manage`` permission.
Delegates to application-layer command/query handlers via Dishka DI.
"""

import uuid

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Depends, status

from src.modules.catalog.application.commands.add_external_product_media import (
    AddExternalProductMediaCommand,
    AddExternalProductMediaHandler,
    AddExternalProductMediaResult,
)
from src.modules.catalog.application.commands.add_product_media import (
    AddProductMediaCommand,
    AddProductMediaHandler,
    AddProductMediaResult,
)
from src.modules.catalog.application.commands.confirm_product_media import (
    ConfirmProductMediaCommand,
    ConfirmProductMediaHandler,
)
from src.modules.catalog.application.commands.delete_product_media import (
    DeleteProductMediaCommand,
    DeleteProductMediaHandler,
)
from src.modules.catalog.application.queries.list_product_media import (
    ListProductMediaHandler,
)
from src.modules.catalog.presentation.schemas import (
    ProductMediaExternalRequest,
    ProductMediaResponse,
    ProductMediaUploadRequest,
    ProductMediaUploadResponse,
)
from src.modules.identity.presentation.dependencies import RequirePermission

product_media_router = APIRouter(
    prefix="/products/{product_id}/media",
    tags=["Product Media"],
    route_class=DishkaRoute,
)


@product_media_router.post(
    path="/upload",
    status_code=status.HTTP_201_CREATED,
    response_model=ProductMediaUploadResponse,
    summary="Reserve media upload slot",
    description="Generate a presigned S3 PUT URL for uploading a media file.",
    dependencies=[Depends(RequirePermission(codename="catalog:manage"))],
)
async def request_media_upload(
    product_id: uuid.UUID,
    request: ProductMediaUploadRequest,
    handler: FromDishka[AddProductMediaHandler],
) -> ProductMediaUploadResponse:
    """Generate a presigned S3 PUT URL for uploading a media file."""
    cmd = AddProductMediaCommand(
        product_id=product_id,
        attribute_value_id=request.attribute_value_id,
        media_type=request.media_type,
        role=request.role,
        content_type=request.content_type,
        sort_order=request.sort_order,
    )
    result: AddProductMediaResult = await handler.handle(cmd)
    return ProductMediaUploadResponse(
        id=result.media_id,
        presigned_upload_url=result.presigned_upload_url,
        object_key=result.object_key,
    )


@product_media_router.post(
    path="/external",
    status_code=status.HTTP_201_CREATED,
    response_model=ProductMediaResponse,
    summary="Add external media URL",
    description="Add an externally hosted media asset to a product.",
    dependencies=[Depends(RequirePermission(codename="catalog:manage"))],
)
async def add_external_media(
    product_id: uuid.UUID,
    request: ProductMediaExternalRequest,
    handler: FromDishka[AddExternalProductMediaHandler],
) -> ProductMediaResponse:
    """Add an externally hosted media asset (e.g. YouTube video) to a product."""
    cmd = AddExternalProductMediaCommand(
        product_id=product_id,
        attribute_value_id=request.attribute_value_id,
        media_type=request.media_type,
        role=request.role,
        external_url=request.external_url,
        sort_order=request.sort_order,
    )
    result: AddExternalProductMediaResult = await handler.handle(cmd)
    return ProductMediaResponse(
        id=result.media_id,
        product_id=result.product_id,
        attribute_value_id=result.attribute_value_id,
        media_type=result.media_type,
        role=result.role,
        sort_order=result.sort_order,
        processing_status=result.processing_status,
        public_url=result.public_url,
        is_external=result.is_external,
        external_url=result.external_url,
    )


@product_media_router.post(
    path="/{media_id}/confirm",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Confirm media upload",
    description="Confirm that a media file was uploaded to S3 and trigger processing.",
    dependencies=[Depends(RequirePermission(codename="catalog:manage"))],
)
async def confirm_media_upload(
    product_id: uuid.UUID,
    media_id: uuid.UUID,
    handler: FromDishka[ConfirmProductMediaHandler],
) -> None:
    """Confirm that a media file was uploaded to S3. Triggers AI processing."""
    cmd = ConfirmProductMediaCommand(product_id=product_id, media_id=media_id)
    await handler.handle(cmd)


@product_media_router.get(
    path="",
    status_code=status.HTTP_200_OK,
    response_model=list[ProductMediaResponse],
    summary="List product media",
    description="Return all media assets for the given product.",
    dependencies=[Depends(RequirePermission(codename="catalog:read"))],
)
async def list_product_media(
    product_id: uuid.UUID,
    handler: FromDishka[ListProductMediaHandler],
) -> list[ProductMediaResponse]:
    """List all media assets for a product."""
    items = await handler.handle(product_id)
    return [
        ProductMediaResponse(
            id=m.id,
            product_id=m.product_id,
            attribute_value_id=m.attribute_value_id,
            media_type=m.media_type,
            role=m.role,
            sort_order=m.sort_order,
            processing_status=m.processing_status,
            public_url=m.public_url,
            is_external=m.is_external,
            external_url=m.external_url,
        )
        for m in items
    ]


@product_media_router.delete(
    path="/{media_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a media asset",
    description="Delete a media asset and its associated S3 files.",
    dependencies=[Depends(RequirePermission(codename="catalog:manage"))],
)
async def delete_product_media(
    product_id: uuid.UUID,
    media_id: uuid.UUID,
    handler: FromDishka[DeleteProductMediaHandler],
) -> None:
    """Delete a media asset and its S3 files."""
    cmd = DeleteProductMediaCommand(product_id=product_id, media_id=media_id)
    await handler.handle(cmd)
