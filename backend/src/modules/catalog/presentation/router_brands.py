"""
FastAPI router for Brand CRUD endpoints.

All mutating endpoints require the ``catalog:manage`` permission.
Read endpoints require the ``catalog:read`` permission (admin use).
Public storefront access is served by the separate storefront router.
Delegates to application-layer command/query handlers via Dishka DI.
"""

import uuid

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Depends, Query, Response, status

from src.modules.catalog.application.commands.bulk_create_brands import (
    BulkBrandItem,
    BulkCreateBrandsCommand,
    BulkCreateBrandsHandler,
)
from src.modules.catalog.application.commands.create_brand import (
    CreateBrandCommand,
    CreateBrandHandler,
    CreateBrandResult,
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
    BulkCreateBrandsRequest,
    BulkCreateBrandsResponse,
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
    command = CreateBrandCommand(
        name=request.name,
        slug=request.slug,
        logo_url=request.logo_url,
        logo_storage_object_id=request.logo_storage_object_id,
    )
    result: CreateBrandResult = await handler.handle(command)
    return BrandCreateResponse(id=result.brand_id)


@brand_router.post(
    path="/bulk",
    status_code=status.HTTP_201_CREATED,
    response_model=BulkCreateBrandsResponse,
    summary="Bulk-create brands (max 100)",
    description="Create multiple brands in a single transaction. Idempotent slugs are rejected.",
    dependencies=[Depends(RequirePermission(codename="catalog:manage"))],
)
async def bulk_create_brands(
    request: BulkCreateBrandsRequest,
    handler: FromDishka[BulkCreateBrandsHandler],
) -> BulkCreateBrandsResponse:
    command = BulkCreateBrandsCommand(
        items=[
            BulkBrandItem(name=item.name, slug=item.slug, logo_url=item.logo_url)
            for item in request.items
        ],
        skip_existing=request.skip_existing,
    )
    result = await handler.handle(command)
    return BulkCreateBrandsResponse(
        created_count=result.created_count,
        skipped_count=result.skipped_count,
        ids=result.ids,
        skipped_slugs=result.skipped_slugs,
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
    response: Response,
    handler: FromDishka[ListBrandsHandler],
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
) -> BrandListResponse:
    response.headers["Cache-Control"] = "no-store"
    query = ListBrandsQuery(offset=offset, limit=limit)
    result: BrandListReadModel = await handler.handle(query)
    return BrandListResponse(
        items=[
            BrandResponse(
                id=item.id,
                name=item.name,
                slug=item.slug,
                logo_url=item.logo_url,
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
    response: Response,
    handler: FromDishka[GetBrandHandler],
) -> BrandResponse:
    response.headers["Cache-Control"] = "no-store"
    result: BrandReadModel = await handler.handle(brand_id)
    return BrandResponse(
        id=result.id,
        name=result.name,
        slug=result.slug,
        logo_url=result.logo_url,
    )


@brand_router.patch(
    path="/{brand_id}",
    status_code=status.HTTP_200_OK,
    response_model=BrandResponse,
    summary="Update a brand",
    description="Partially update brand fields like name, slug, or logo.",
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
