"""
FastAPI router for storefront search endpoints.

Public read-only endpoints for full-text product search and autocomplete
suggestions.  No authentication required.

URL paths (under /api/v1/catalog):
    GET /storefront/search          — Full-text product search
    GET /storefront/search/suggest  — Autocomplete suggestions
"""

import uuid

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Query, Request, Response, status

from src.modules.catalog.application.queries.compute_facets import (
    ComputeFacetsHandler,
    ComputeFacetsQuery,
)
from src.modules.catalog.application.queries.search_products import (
    SearchProductsHandler,
    SearchProductsQuery,
)
from src.modules.catalog.application.queries.search_suggest import (
    SearchSuggestHandler,
    SearchSuggestQuery,
)
from src.modules.catalog.presentation.schemas_storefront import (
    SearchSuggestionResponse,
    StorefrontPLPResponse,
    StorefrontProductCardResponse,
)

storefront_search_router = APIRouter(
    prefix="/storefront/search",
    tags=["Storefront Search"],
    route_class=DishkaRoute,
)


# ---------------------------------------------------------------------------
# Shared helpers (same as router_storefront_products.py)
# ---------------------------------------------------------------------------


def _project_i18n(i18n_dict: dict[str, str], lang: str) -> str:
    if lang in i18n_dict:
        return i18n_dict[lang]
    if i18n_dict:
        return next(iter(i18n_dict.values()))
    return ""


def _search_cache_control(lang: str | None) -> str:
    if lang:
        return "private, max-age=60"
    return "public, max-age=60, s-maxage=60, stale-while-revalidate=300"


def _parse_attribute_filters(request: Request) -> dict[str, list[str]] | None:
    filters: dict[str, list[str]] = {}
    for key, value in request.query_params.multi_items():
        if key.startswith("attr."):
            code = key[5:]
            if code and value:
                filters.setdefault(code, []).append(value)
    for code in filters:
        filters[code] = sorted(set(filters[code]))
    return filters or None


# ---------------------------------------------------------------------------
# Full-text product search
# ---------------------------------------------------------------------------


@storefront_search_router.get(
    path="",
    status_code=status.HTTP_200_OK,
    response_model=StorefrontPLPResponse,
    summary="Search products (full-text)",
    description=(
        "Full-text search across product titles, descriptions, and tags.  "
        "Returns cursor-paginated product cards with optional facets (requires "
        "category_id when include_facets=true).  Supports the same filters as PLP."
    ),
)
async def search_products(
    request: Request,
    handler: FromDishka[SearchProductsHandler],
    facets_handler: FromDishka[ComputeFacetsHandler],
    response: Response,
    q: str = Query(
        ..., min_length=1, max_length=200, description="Search query text"
    ),
    category_id: uuid.UUID | None = Query(
        None, description="Optional: scope search to a category"
    ),
    brand_id: list[uuid.UUID] | None = Query(
        None, description="Filter by brand IDs (OR semantics)"
    ),
    price_min: int | None = Query(
        None, ge=0, description="Min price (smallest currency unit)"
    ),
    price_max: int | None = Query(
        None, ge=0, description="Max price (smallest currency unit)"
    ),
    in_stock: bool | None = Query(None, description="Only show in-stock products"),
    sort: str = Query(
        "relevant",
        pattern="^(relevant|popular|newest|price_asc|price_desc)$",
        description="Sort order (relevant = FTS rank)",
    ),
    limit: int = Query(24, ge=1, le=48, description="Page size"),
    cursor: str | None = Query(None, description="Opaque pagination cursor"),
    include_total: bool = Query(False, description="Include total count (slower)"),
    include_facets: bool = Query(
        False,
        description="Include facet counts (requires category_id)",
    ),
    lang: str | None = Query(
        None,
        min_length=2,
        max_length=5,
        description="Locale code for i18n projection",
    ),
) -> StorefrontPLPResponse:
    attribute_filters = _parse_attribute_filters(request)

    query = SearchProductsQuery(
        q=q,
        category_id=category_id,
        brand_ids=brand_id,
        price_min=price_min,
        price_max=price_max,
        in_stock=in_stock,
        attribute_filters=attribute_filters,
        sort=sort,
        limit=limit,
        cursor=cursor,
        include_total=include_total,
    )
    result = await handler.handle(query)

    response.headers["Cache-Control"] = _search_cache_control(lang)

    cards = []
    for item in result.items:
        card = StorefrontProductCardResponse.model_validate(item, from_attributes=True)
        if lang:
            card.title = _project_i18n(card.title_i18n, lang)
        cards.append(card)

    facets_data = None
    if include_facets and category_id:
        from src.modules.catalog.presentation.schemas_storefront import (
            FacetResultResponse,
        )

        facets_query = ComputeFacetsQuery(
            category_id=category_id,
            brand_ids=brand_id,
            price_min=price_min,
            price_max=price_max,
            in_stock=in_stock,
            attribute_filters=attribute_filters,
        )
        facets_result = await facets_handler.handle(facets_query)
        facets_data = FacetResultResponse.model_validate(
            facets_result, from_attributes=True
        )

    return StorefrontPLPResponse(
        items=cards,
        has_next=result.has_next,
        next_cursor=result.next_cursor,
        total=result.total,
        facets=facets_data,
    )


# ---------------------------------------------------------------------------
# Autocomplete suggestions
# ---------------------------------------------------------------------------


@storefront_search_router.get(
    path="/suggest",
    status_code=status.HTTP_200_OK,
    response_model=list[SearchSuggestionResponse],
    summary="Autocomplete search suggestions",
    description=(
        "Returns mixed autocomplete suggestions (categories, brands, products) "
        "matching a prefix.  Minimum 2 characters required."
    ),
)
async def search_suggest(
    handler: FromDishka[SearchSuggestHandler],
    response: Response,
    q: str = Query(
        ..., min_length=2, max_length=100, description="Search prefix (min 2 chars)"
    ),
    limit: int = Query(5, ge=1, le=10, description="Max suggestions to return"),
    lang: str | None = Query(
        None,
        min_length=2,
        max_length=5,
        description="Preferred locale for suggestion text",
    ),
) -> list[SearchSuggestionResponse]:
    query = SearchSuggestQuery(q=q, limit=limit, lang=lang)
    results = await handler.handle(query)

    response.headers["Cache-Control"] = "public, max-age=120, s-maxage=120"

    return [
        SearchSuggestionResponse.model_validate(item, from_attributes=True)
        for item in results
    ]
