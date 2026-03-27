"""
FastAPI router for Category CRUD and tree endpoints.

All mutating endpoints require the ``catalog:manage`` permission.
Read endpoints require the ``catalog:read`` permission (admin use).
Public storefront access is served by the separate storefront router.
Delegates to application-layer command/query handlers via Dishka DI.
"""

import uuid

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Depends, Query, Response, status

from src.modules.catalog.application.commands.bulk_create_categories import (
    BulkCategoryItem,
    BulkCreateCategoriesCommand,
    BulkCreateCategoriesHandler,
)
from src.modules.catalog.application.commands.create_category import (
    CreateCategoryCommand,
    CreateCategoryHandler,
    CreateCategoryResult,
)
from src.modules.catalog.application.commands.delete_category import (
    DeleteCategoryCommand,
    DeleteCategoryHandler,
)
from src.modules.catalog.application.commands.update_category import (
    UpdateCategoryCommand,
    UpdateCategoryHandler,
    UpdateCategoryResult,
)
from src.modules.catalog.application.queries.get_category import GetCategoryHandler
from src.modules.catalog.application.queries.get_category_tree import (
    GetCategoryTreeHandler,
)
from src.modules.catalog.application.queries.list_categories import (
    ListCategoriesHandler,
    ListCategoriesQuery,
)
from src.modules.catalog.application.queries.read_models import (
    CategoryListReadModel,
    CategoryNode,
    CategoryReadModel,
)
from src.modules.catalog.presentation.schemas import (
    BulkCategoryCreatedItemResponse,
    BulkCreateCategoriesRequest,
    BulkCreateCategoriesResponse,
    CategoryCreateRequest,
    CategoryCreateResponse,
    CategoryListResponse,
    CategoryResponse,
    CategoryTreeResponse,
    CategoryUpdateRequest,
)
from src.modules.catalog.presentation.update_helpers import build_update_command
from src.modules.identity.presentation.dependencies import RequirePermission

category_router = APIRouter(
    prefix="/categories",
    tags=["Categories"],
    route_class=DishkaRoute,
)


@category_router.post(
    path="",
    status_code=status.HTTP_201_CREATED,
    response_model=CategoryCreateResponse,
    summary="Create a new category",
    description="Creates a category in the hierarchy.",
    dependencies=[Depends(RequirePermission(codename="catalog:manage"))],
)
async def create_category(
    request: CategoryCreateRequest,
    handler: FromDishka[CreateCategoryHandler],
) -> CategoryCreateResponse:
    command = CreateCategoryCommand(
        name_i18n=request.name_i18n,
        slug=request.slug,
        parent_id=request.parent_id,
        sort_order=request.sort_order,
        template_id=request.template_id,
    )
    category: CreateCategoryResult = await handler.handle(command)
    return CategoryCreateResponse(
        id=category.id, message="Category created successfully"
    )


@category_router.post(
    path="/bulk",
    status_code=status.HTTP_201_CREATED,
    response_model=BulkCreateCategoriesResponse,
    summary="Bulk-create categories (max 200)",
    description=(
        "Create multiple categories in a single transaction. "
        "Use 'ref' / 'parentRef' to build a tree within one request."
    ),
    dependencies=[Depends(RequirePermission(codename="catalog:manage"))],
)
async def bulk_create_categories(
    request: BulkCreateCategoriesRequest,
    handler: FromDishka[BulkCreateCategoriesHandler],
) -> BulkCreateCategoriesResponse:
    command = BulkCreateCategoriesCommand(
        items=[
            BulkCategoryItem(
                name_i18n=item.name_i18n,
                slug=item.slug,
                parent_id=item.parent_id,
                parent_ref=item.parent_ref,
                ref=item.ref,
                sort_order=item.sort_order,
                template_id=item.template_id,
            )
            for item in request.items
        ],
        skip_existing=request.skip_existing,
    )
    result = await handler.handle(command)
    return BulkCreateCategoriesResponse(
        created_count=result.created_count,
        skipped_count=result.skipped_count,
        created=[
            BulkCategoryCreatedItemResponse(
                id=c.id,
                slug=c.slug,
                full_slug=c.full_slug,
                level=c.level,
                ref=c.ref,
            )
            for c in result.created
        ],
        skipped_slugs=result.skipped_slugs,
    )


@category_router.get(
    path="/tree",
    status_code=status.HTTP_200_OK,
    response_model=list[CategoryTreeResponse],
    summary="Get the category tree",
    description="Returns the full catalog as a nested tree",
    dependencies=[Depends(RequirePermission(codename="catalog:read"))],
)
async def get_category_tree(
    response: Response,
    handler: FromDishka[GetCategoryTreeHandler],
    max_depth: int | None = Query(
        default=None, ge=1, le=10, description="Maximum tree depth to return"
    ),
) -> list[CategoryTreeResponse]:
    response.headers["Cache-Control"] = "public, max-age=300, s-maxage=3600"
    roots: list[CategoryNode] = await handler.handle(max_depth=max_depth)
    return [CategoryTreeResponse.model_validate(r, from_attributes=True) for r in roots]


@category_router.get(
    path="",
    status_code=status.HTTP_200_OK,
    response_model=CategoryListResponse,
    summary="List categories (paginated)",
    description="Retrieve a paginated list of all categories.",
    dependencies=[Depends(RequirePermission(codename="catalog:read"))],
)
async def list_categories(
    response: Response,
    handler: FromDishka[ListCategoriesHandler],
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
) -> CategoryListResponse:
    response.headers["Cache-Control"] = "no-store"
    query = ListCategoriesQuery(offset=offset, limit=limit)
    result: CategoryListReadModel = await handler.handle(query)
    return CategoryListResponse(
        items=[
            CategoryResponse(
                id=item.id,
                name_i18n=item.name_i18n,
                slug=item.slug,
                full_slug=item.full_slug,
                level=item.level,
                sort_order=item.sort_order,
                parent_id=item.parent_id,
            )
            for item in result.items
        ],
        total=result.total,
        offset=result.offset,
        limit=result.limit,
    )


@category_router.get(
    path="/{category_id}",
    status_code=status.HTTP_200_OK,
    response_model=CategoryResponse,
    summary="Get category by ID",
    description="Retrieve a single category by its unique identifier.",
    dependencies=[Depends(RequirePermission(codename="catalog:read"))],
)
async def get_category(
    category_id: uuid.UUID,
    response: Response,
    handler: FromDishka[GetCategoryHandler],
) -> CategoryResponse:
    response.headers["Cache-Control"] = "no-store"
    result: CategoryReadModel = await handler.handle(category_id)
    return CategoryResponse(
        id=result.id,
        name_i18n=result.name_i18n,
        slug=result.slug,
        full_slug=result.full_slug,
        level=result.level,
        sort_order=result.sort_order,
        parent_id=result.parent_id,
    )


@category_router.patch(
    path="/{category_id}",
    status_code=status.HTTP_200_OK,
    response_model=CategoryResponse,
    summary="Update a category",
    description="Partially update category fields. Only provided fields are modified.",
    dependencies=[Depends(RequirePermission(codename="catalog:manage"))],
)
async def update_category(
    category_id: uuid.UUID,
    request: CategoryUpdateRequest,
    handler: FromDishka[UpdateCategoryHandler],
) -> CategoryResponse:
    command = build_update_command(
        request,
        UpdateCategoryCommand,
        category_id=category_id,
    )
    result: UpdateCategoryResult = await handler.handle(command)
    return CategoryResponse(
        id=result.id,
        name_i18n=result.name_i18n,
        slug=result.slug,
        full_slug=result.full_slug,
        level=result.level,
        sort_order=result.sort_order,
        parent_id=result.parent_id,
    )


@category_router.delete(
    path="/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a category",
    description="Permanently delete a category and its subtree.",
    dependencies=[Depends(RequirePermission(codename="catalog:manage"))],
)
async def delete_category(
    category_id: uuid.UUID,
    handler: FromDishka[DeleteCategoryHandler],
) -> None:
    command = DeleteCategoryCommand(category_id=category_id)
    await handler.handle(command)
