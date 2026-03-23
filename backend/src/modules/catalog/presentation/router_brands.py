"""
FastAPI router for Brand CRUD and logo management endpoints.

All mutating endpoints require the ``catalog:manage`` permission.
Read endpoints require the ``catalog:read`` permission (admin use).
Public storefront access is served by the separate storefront router.
Delegates to application-layer command/query handlers via Dishka DI.
"""

import uuid

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Depends, Query, status

from src.modules.catalog.application.commands.confirm_brand_logo import (
    ConfirmBrandLogoUploadCommand,
    ConfirmBrandLogoUploadHandler,
)
from src.modules.catalog.application.commands.create_brand import (
    CreateBrandCommand,
    CreateBrandHandler,
    CreateBrandResult,
    LogoMetadata,
)
from src.modules.catalog.application.commands.delete_brand import (
    DeleteBrandCommand,
    DeleteBrandHandler,
)
from src.modules.catalog.application.commands.update_brand import (
    UpdateBrandCommand,
    UpdateBrandHandler,
    UpdateBrandResult,
)
from src.modules.catalog.application.queries.get_brand import GetBrandHandler
from src.modules.catalog.application.queries.list_brands import (
    ListBrandsHandler,
    ListBrandsQuery,
)
from src.modules.catalog.application.queries.read_models import (
    BrandListReadModel,
    BrandReadModel,
)
from src.modules.catalog.presentation.schemas import (
    BrandCreateRequest,
    BrandCreateResponse,
    BrandListResponse,
    BrandResponse,
    BrandUpdateRequest,
    LogoConfirmResponse,
)
from src.modules.catalog.presentation.update_helpers import build_update_command
from src.modules.identity.presentation.dependencies import RequirePermission

brand_router = APIRouter(
    prefix="/brands",
    tags=["Brands"],
    route_class=DishkaRoute,
)


@brand_router.post(
    path="",
    status_code=status.HTTP_201_CREATED,
    response_model=BrandCreateResponse,
    summary="Create a new brand",
    description="Create a new brand with name, slug, and optional logo.",
    dependencies=[Depends(RequirePermission(codename="catalog:manage"))],
)
async def create_brand(
    request: BrandCreateRequest,
    handler: FromDishka[CreateBrandHandler],
) -> BrandCreateResponse:
    logo_meta = None
    if request.logo:
        logo_meta = LogoMetadata(
            filename=request.logo.filename,
            content_type=request.logo.content_type,
            size=request.logo.size,
        )

    command = CreateBrandCommand(
        name=request.name,
        slug=request.slug,
        logo=logo_meta,
    )
    result: CreateBrandResult = await handler.handle(command)
    return BrandCreateResponse(
        id=result.brand_id,
        presigned_upload_url=result.presigned_upload_url,
        object_key=result.object_key,
    )


@brand_router.get(
    path="",
    status_code=status.HTTP_200_OK,
    response_model=BrandListResponse,
    summary="List brands (paginated)",
    description="Retrieve a paginated list of all brands.",
    dependencies=[Depends(RequirePermission(codename="catalog:read"))],
)
async def list_brands(
    handler: FromDishka[ListBrandsHandler],
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
) -> BrandListResponse:
    query = ListBrandsQuery(offset=offset, limit=limit)
    result: BrandListReadModel = await handler.handle(query)
    return BrandListResponse(
        items=[
            BrandResponse(
                id=item.id,
                name=item.name,
                slug=item.slug,
                logo_url=item.logo_url,
                logo_status=item.logo_status,
            )
            for item in result.items
        ],
        total=result.total,
        offset=result.offset,
        limit=result.limit,
    )


@brand_router.get(
    path="/{brand_id}",
    status_code=status.HTTP_200_OK,
    response_model=BrandResponse,
    summary="Get brand by ID",
    description="Retrieve a single brand by its unique identifier.",
    dependencies=[Depends(RequirePermission(codename="catalog:read"))],
)
async def get_brand(
    brand_id: uuid.UUID,
    handler: FromDishka[GetBrandHandler],
) -> BrandResponse:
    result: BrandReadModel = await handler.handle(brand_id)
    return BrandResponse(
        id=result.id,
        name=result.name,
        slug=result.slug,
        logo_url=result.logo_url,
        logo_status=result.logo_status,
    )


@brand_router.patch(
    path="/{brand_id}",
    status_code=status.HTTP_200_OK,
    response_model=BrandResponse,
    summary="Update a brand",
    description="Partially update brand fields like name or slug.",
    dependencies=[Depends(RequirePermission(codename="catalog:manage"))],
)
async def update_brand(
    brand_id: uuid.UUID,
    request: BrandUpdateRequest,
    handler: FromDishka[UpdateBrandHandler],
) -> BrandResponse:
    command = build_update_command(
        request,
        UpdateBrandCommand,
        brand_id=brand_id,
    )
    result: UpdateBrandResult = await handler.handle(command)
    return BrandResponse(
        id=result.id,
        name=result.name,
        slug=result.slug,
        logo_url=result.logo_url,
        logo_status=result.logo_status,
    )


@brand_router.delete(
    path="/{brand_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a brand",
    description="Permanently delete a brand by its ID.",
    dependencies=[Depends(RequirePermission(codename="catalog:manage"))],
)
async def delete_brand(
    brand_id: uuid.UUID,
    handler: FromDishka[DeleteBrandHandler],
) -> None:
    command = DeleteBrandCommand(brand_id=brand_id)
    await handler.handle(command)


@brand_router.post(
    path="/{brand_id}/logo/confirm",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=LogoConfirmResponse,
    summary="Confirm logo upload",
    description="Confirm that a logo was uploaded to S3 and start processing.",
    dependencies=[Depends(RequirePermission(codename="catalog:manage"))],
)
async def confirm_logo_upload(
    brand_id: uuid.UUID,
    handler: FromDishka[ConfirmBrandLogoUploadHandler],
) -> LogoConfirmResponse:
    command = ConfirmBrandLogoUploadCommand(brand_id=brand_id)
    await handler.handle(command)
    return LogoConfirmResponse()
