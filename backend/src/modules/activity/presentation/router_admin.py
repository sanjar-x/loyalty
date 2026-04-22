"""
FastAPI router for admin-facing activity analytics.

Exposes the read side of the activity module over Redis sorted sets:

* ``GET /admin/analytics/trending`` — top trending product IDs with scores
* ``GET /admin/analytics/search``   — popular + zero-result queries

All endpoints require ``catalog:manage``.  They degrade gracefully when
Redis is unavailable — handlers return empty lists rather than erroring.
"""

from __future__ import annotations

import uuid

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Depends, Query

from src.modules.activity.presentation.schemas import (
    SearchAnalyticsResponse,
    SearchQueryEntry,
    TrendingProductEntry,
    TrendingProductsResponse,
)
from src.modules.identity.presentation.dependencies import RequirePermission
from src.shared.interfaces.activity import IActivityQueryService

activity_admin_router = APIRouter(
    prefix="/admin/analytics",
    tags=["Admin — Analytics"],
    route_class=DishkaRoute,
)


@activity_admin_router.get(
    "/trending",
    response_model=TrendingProductsResponse,
    summary="Top trending products",
    dependencies=[Depends(RequirePermission(codename="catalog:manage"))],
)
async def get_trending_products(
    query_service: FromDishka[IActivityQueryService],
    limit: int = Query(50, ge=1, le=500),
    window: str = Query("weekly", pattern=r"^(daily|weekly)$"),
    category_id: uuid.UUID | None = Query(None),
) -> TrendingProductsResponse:
    ranked = await query_service.get_trending_products(
        limit=limit, window=window, category_id=category_id
    )

    items: list[TrendingProductEntry] = []
    for entry in ranked:
        try:
            pid = uuid.UUID(entry.entity_id)
        except ValueError:
            continue
        items.append(TrendingProductEntry(product_id=pid, score=entry.score))

    return TrendingProductsResponse(
        window=window,
        category_id=category_id,
        items=items,
    )


@activity_admin_router.get(
    "/search",
    response_model=SearchAnalyticsResponse,
    summary="Search analytics — popular and zero-result queries",
    dependencies=[Depends(RequirePermission(codename="catalog:manage"))],
)
async def get_search_analytics(
    query_service: FromDishka[IActivityQueryService],
    limit: int = Query(50, ge=1, le=500),
) -> SearchAnalyticsResponse:
    popular = await query_service.get_popular_search_queries(limit=limit)
    zero_results = await query_service.get_zero_result_queries(limit=limit)

    return SearchAnalyticsResponse(
        popular=[
            SearchQueryEntry(query=entry.entity_id, count=entry.score)
            for entry in popular
        ],
        zero_results=[
            SearchQueryEntry(query=entry.entity_id, count=entry.score)
            for entry in zero_results
        ],
    )
