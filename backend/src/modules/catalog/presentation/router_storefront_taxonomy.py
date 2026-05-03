"""Public taxonomy endpoints for the customer storefront.

Customer apps need read-only access to:

* the full category tree (for navigation menus / mega-dropdown / sitemap)
* the flat list of categories (for filters, breadcrumbs)
* a single category by ID (for direct deep-links)
* the list of brands (for brand-pickers, brand-pages)
* a single brand by ID (for the brand page)

These endpoints reuse the same query handlers as
``router_admin_categories.py`` / ``router_admin_brands.py`` but expose
them under ``/storefront/*`` without auth dependencies, with longer
cache headers, and trimmed payloads (admin-only fields are dropped at
the schema layer where applicable).
"""

from __future__ import annotations

import uuid

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Query, Response, status

from src.modules.catalog.application.queries.get_brand import GetBrandHandler
from src.modules.catalog.application.queries.get_category import GetCategoryHandler
from src.modules.catalog.application.queries.get_category_tree import (
    CategoryNode,
    GetCategoryTreeHandler,
)
from src.modules.catalog.application.queries.list_brands import (
    ListBrandsHandler,
    ListBrandsQuery,
)
from src.modules.catalog.application.queries.list_categories import (
    ListCategoriesHandler,
    ListCategoriesQuery,
)
from src.modules.catalog.application.queries.read_models import (
    BrandListReadModel,
    BrandReadModel,
    CategoryListReadModel,
    CategoryReadModel,
)
from src.modules.catalog.presentation.schemas import (
    BrandListResponse,
    BrandResponse,
    CategoryListResponse,
    CategoryResponse,
    CategoryTreeResponse,
)

storefront_taxonomy_router = APIRouter(
    prefix="/storefront",
    tags=["Storefront / Taxonomy"],
    route_class=DishkaRoute,
)


# ---------------------------------------------------------------------------
# Categories
# ---------------------------------------------------------------------------


@storefront_taxonomy_router.get(
    "/categories/tree",
    status_code=status.HTTP_200_OK,
    response_model=list[CategoryTreeResponse],
    summary="Public category tree (storefront navigation)",
)
async def storefront_category_tree(
    response: Response,
    handler: FromDishka[GetCategoryTreeHandler],
    max_depth: int | None = Query(default=None, ge=1, le=10),
) -> list[CategoryTreeResponse]:
    response.headers["Cache-Control"] = "public, max-age=300, s-maxage=3600"
    roots: list[CategoryNode] = await handler.handle(max_depth=max_depth)
    return [CategoryTreeResponse.model_validate(r, from_attributes=True) for r in roots]


@storefront_taxonomy_router.get(
    "/categories",
    status_code=status.HTTP_200_OK,
    response_model=CategoryListResponse,
    summary="Public flat category list",
)
async def storefront_list_categories(
    response: Response,
    handler: FromDishka[ListCategoriesHandler],
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=200, ge=1, le=500),
) -> CategoryListResponse:
    response.headers["Cache-Control"] = "public, max-age=300, s-maxage=3600"
    result: CategoryListReadModel = await handler.handle(
        ListCategoriesQuery(offset=offset, limit=limit)
    )
    return CategoryListResponse(
        items=[
            CategoryResponse.model_validate(item, from_attributes=True)
            for item in result.items
        ],
        total=result.total,
        offset=result.offset,
        limit=result.limit,
    )


@storefront_taxonomy_router.get(
    "/categories/{category_id}",
    status_code=status.HTTP_200_OK,
    response_model=CategoryResponse,
    summary="Public category detail",
)
async def storefront_get_category(
    category_id: uuid.UUID,
    response: Response,
    handler: FromDishka[GetCategoryHandler],
) -> CategoryResponse:
    response.headers["Cache-Control"] = "public, max-age=300, s-maxage=3600"
    result: CategoryReadModel = await handler.handle(category_id)
    return CategoryResponse.model_validate(result, from_attributes=True)


# ---------------------------------------------------------------------------
# Brands
# ---------------------------------------------------------------------------


@storefront_taxonomy_router.get(
    "/brands",
    status_code=status.HTTP_200_OK,
    response_model=BrandListResponse,
    summary="Public brand list",
)
async def storefront_list_brands(
    response: Response,
    handler: FromDishka[ListBrandsHandler],
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=200, ge=1, le=500),
) -> BrandListResponse:
    response.headers["Cache-Control"] = "public, max-age=300, s-maxage=3600"
    result: BrandListReadModel = await handler.handle(
        ListBrandsQuery(offset=offset, limit=limit)
    )
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


@storefront_taxonomy_router.get(
    "/brands/{brand_id}",
    status_code=status.HTTP_200_OK,
    response_model=BrandResponse,
    summary="Public brand detail",
)
async def storefront_get_brand(
    brand_id: uuid.UUID,
    response: Response,
    handler: FromDishka[GetBrandHandler],
) -> BrandResponse:
    response.headers["Cache-Control"] = "public, max-age=300, s-maxage=3600"
    result: BrandReadModel = await handler.handle(brand_id)
    return BrandResponse(
        id=result.id,
        name=result.name,
        slug=result.slug,
        logo_url=result.logo_url,
    )
