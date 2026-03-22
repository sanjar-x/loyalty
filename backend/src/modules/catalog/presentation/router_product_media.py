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
    "/upload",
    status_code=status.HTTP_201_CREATED,
    response_model=ProductMediaUploadResponse,
    summary="Reserve media upload slot",
    dependencies=[Depends(RequirePermission(codename="catalog:manage"))],
)
async def request_media_upload(
    product_id: uuid.UUID,
    body: ProductMediaUploadRequest,
    handler: FromDishka[AddProductMediaHandler],
) -> ProductMediaUploadResponse:
    """Generate a presigned S3 PUT URL for uploading a media file."""
    cmd = AddProductMediaCommand(
        product_id=product_id,
        attribute_value_id=body.attribute_value_id,
        media_type=body.media_type,
        role=body.role,
        content_type=body.content_type,
        sort_order=body.sort_order,
    )
    result: AddProductMediaResult = await handler.handle(cmd)
    return ProductMediaUploadResponse(
        id=result.media_id,
        presigned_upload_url=result.presigned_upload_url,
        object_key=result.object_key,
    )


@product_media_router.post(
    "/external",
    status_code=status.HTTP_201_CREATED,
    response_model=ProductMediaResponse,
    summary="Add external media URL",
    dependencies=[Depends(RequirePermission(codename="catalog:manage"))],
)
async def add_external_media(
    product_id: uuid.UUID,
    body: ProductMediaExternalRequest,
    handler: FromDishka[AddExternalProductMediaHandler],
) -> ProductMediaResponse:
    """Add an externally hosted media asset (e.g. YouTube video) to a product."""
    cmd = AddExternalProductMediaCommand(
        product_id=product_id,
        attribute_value_id=body.attribute_value_id,
        media_type=body.media_type,
        role=body.role,
        external_url=body.external_url,
        sort_order=body.sort_order,
    )
    result: AddExternalProductMediaResult = await handler.handle(cmd)
    return ProductMediaResponse(
        id=result.media_id,
        product_id=product_id,
        attribute_value_id=body.attribute_value_id,
        media_type=body.media_type.upper(),
        role=body.role.upper(),
        sort_order=body.sort_order,
        processing_status="COMPLETED",
        public_url=result.public_url,
        is_external=True,
        external_url=body.external_url,
    )


@product_media_router.post(
    "/{media_id}/confirm",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Confirm media upload",
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
    "",
    response_model=list[ProductMediaResponse],
    summary="List product media",
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
    "/{media_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a media asset",
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
