"""
FastAPI router for storefront trending products.

Public read-only endpoint that surfaces the most-viewed products during a
rolling window.  Rankings come from Redis sorted sets (maintained by
:class:`RedisActivityTracker`), enriched with full product cards through
:class:`GetStorefrontProductCardsByIdsHandler`.

URL paths (under ``/api/v1/catalog``):

* ``GET /storefront/trending`` — global or category-scoped trending cards

The endpoint degrades gracefully when Redis is unavailable — the query
service returns an empty list and the response carries no items.
"""

from __future__ import annotations

import uuid

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Query, Response

from src.modules.catalog.application.queries.get_storefront_cards_by_ids import (
    GetStorefrontProductCardsByIdsHandler,
    GetStorefrontProductCardsByIdsQuery,
)
from src.modules.catalog.presentation.router_storefront_products import (
    _project_i18n,
)
from src.modules.catalog.presentation.schemas_storefront import (
    StorefrontPLPResponse,
    StorefrontProductCardResponse,
)
from src.shared.interfaces.activity import IActivityQueryService

storefront_trending_router = APIRouter(
    prefix="/storefront/trending",
    tags=["Storefront Trending"],
    route_class=DishkaRoute,
)


_TRENDING_CACHE_CONTROL = (
    "public, max-age=120, s-maxage=120, stale-while-revalidate=600"
)


@storefront_trending_router.get(
    "",
    response_model=StorefrontPLPResponse,
    summary="Top trending products",
    description=(
        "Return the most-viewed products within the selected window.  "
        "Ranking comes from Redis sorted sets updated in near-real time.  "
        "When ``category_id`` is provided, returns trending within that "
        "category; otherwise global trending over the ``window`` period."
    ),
)
async def list_trending_products(
    handler: FromDishka[GetStorefrontProductCardsByIdsHandler],
    query_service: FromDishka[IActivityQueryService],
    response: Response,
    limit: int = Query(20, ge=1, le=50, description="Maximum number of cards"),
    window: str = Query(
        "weekly",
        pattern=r"^(daily|weekly)$",
        description="Ranking window (ignored when category_id is set)",
    ),
    category_id: uuid.UUID | None = Query(
        None, description="Optional: scope trending to a category"
    ),
    lang: str | None = Query(
        None, pattern=r"^(ru|en)$", description="Language for title projection"
    ),
) -> StorefrontPLPResponse:
    ranked = await query_service.get_trending_products(
        limit=limit, window=window, category_id=category_id
    )

    product_ids: list[uuid.UUID] = []
    for entry in ranked:
        try:
            product_ids.append(uuid.UUID(entry.entity_id))
        except ValueError:
            # Redis may temporarily hold stale / malformed members; skip.
            continue

    cards = (
        await handler.handle(
            GetStorefrontProductCardsByIdsQuery(product_ids=product_ids)
        )
        if product_ids
        else []
    )

    response.headers["Cache-Control"] = _TRENDING_CACHE_CONTROL

    items: list[StorefrontProductCardResponse] = []
    for card in cards:
        item = StorefrontProductCardResponse.model_validate(card, from_attributes=True)
        if lang:
            item.title = _project_i18n(item.title_i18n, lang)
            for opt in item.variant_options:
                opt.attribute_name = _project_i18n(opt.attribute_name_i18n, lang)
                for ov in opt.values:
                    ov.value = _project_i18n(ov.value_i18n, lang)
        items.append(item)

    return StorefrontPLPResponse(
        items=items,
        has_next=False,
        next_cursor=None,
        total=len(items),
        facets=None,
    )
