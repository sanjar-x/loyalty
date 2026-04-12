"""
FastAPI router for storefront product endpoints (PLP + PDP).

Public read-only endpoints that serve product data for the customer-facing
storefront.  No authentication required.  Responses are cache-friendly with
appropriate Cache-Control headers.

URL paths (under /api/v1/catalog):
    GET /storefront/products          — Product listing (PLP)
    GET /storefront/products/{slug}   — Product detail  (PDP)
"""

import uuid

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Query, Request, Response, status

from src.modules.catalog.application.queries.compute_facets import (
    ComputeFacetsHandler,
    ComputeFacetsQuery,
)
from src.modules.catalog.application.queries.get_storefront_product import (
    GetStorefrontProductHandler,
)
from src.modules.catalog.application.queries.list_storefront_products import (
    ListStorefrontProductsHandler,
    StorefrontProductListQuery,
)
from src.modules.catalog.presentation.schemas_storefront import (
    StorefrontPLPResponse,
    StorefrontProductCardResponse,
    StorefrontProductDetailResponse,
)
from src.shared.exceptions import ValidationError

storefront_products_router = APIRouter(
    prefix="/storefront/products",
    tags=["Storefront Products"],
    route_class=DishkaRoute,
)


# ---------------------------------------------------------------------------
# i18n helpers (shared with router_storefront.py)
# ---------------------------------------------------------------------------


def _project_i18n(i18n_dict: dict[str, str], lang: str) -> str:
    """Project a single locale from an i18n dict with fallback chain."""
    if lang in i18n_dict:
        return i18n_dict[lang]
    if i18n_dict:
        return next(iter(i18n_dict.values()))
    return ""


def _plp_cache_control(lang: str | None) -> str:
    if lang:
        return "private, max-age=60"
    return "public, max-age=60, s-maxage=60, stale-while-revalidate=300"


def _pdp_cache_control(lang: str | None) -> str:
    if lang:
        return "private, max-age=300"
    return "public, max-age=300, s-maxage=300, stale-while-revalidate=600"


def _parse_attribute_filters(request: Request) -> dict[str, list[str]] | None:
    """Extract ``attr.*`` query params from the raw query string.

    Example: ``?attr.color=red&attr.color=blue&attr.size=xl``
    → ``{"color": ["red", "blue"], "size": ["xl"]}``

    Repeated params become multi-valued (not CSV).  Unknown prefix params
    are silently ignored.
    """
    filters: dict[str, list[str]] = {}
    for key, value in request.query_params.multi_items():
        if key.startswith("attr."):
            code = key[5:]  # len("attr.") == 5
            if code and value:
                filters.setdefault(code, []).append(value)
    # Dedupe and sort for cache stability.
    for code in filters:
        filters[code] = sorted(set(filters[code]))
    return filters or None


# ---------------------------------------------------------------------------
# PLP — Product listing
# ---------------------------------------------------------------------------


@storefront_products_router.get(
    path="",
    status_code=status.HTTP_200_OK,
    response_model=StorefrontPLPResponse,
    summary="List products for storefront (PLP)",
    description=(
        "Returns a cursor-paginated list of published product cards for a given "
        "category.  Supports filtering by brand, price range, stock status, and "
        "EAV attribute filters (attr.{code}={slug}).  Optionally includes facet "
        "counts for the filter panel (include_facets=true)."
    ),
)
async def list_storefront_products(
    request: Request,
    handler: FromDishka[ListStorefrontProductsHandler],
    facets_handler: FromDishka[ComputeFacetsHandler],
    response: Response,
    category_id: uuid.UUID = Query(..., description="Category to browse"),
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
        "popular",
        pattern="^(popular|newest|price_asc|price_desc)$",
        description="Sort order",
    ),
    limit: int = Query(24, ge=1, le=48, description="Page size"),
    cursor: str | None = Query(None, description="Opaque pagination cursor"),
    include_total: bool = Query(False, description="Include total count (slower)"),
    include_facets: bool = Query(
        False, description="Include facet counts for the filter panel"
    ),
    lang: str | None = Query(
        None,
        min_length=2,
        max_length=5,
        description="Locale code for i18n projection (e.g. 'ru', 'en')",
    ),
) -> StorefrontPLPResponse:
    attribute_filters = _parse_attribute_filters(request)

    query = StorefrontProductListQuery(
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
    try:
        result = await handler.handle(query)
    except ValueError as exc:
        raise ValidationError(
            message=str(exc),
            error_code="INVALID_CURSOR",
            details={"cursor": cursor},
        ) from exc

    response.headers["Cache-Control"] = _plp_cache_control(lang)

    cards = []
    for item in result.items:
        card = StorefrontProductCardResponse.model_validate(item, from_attributes=True)
        if lang:
            card.title = _project_i18n(card.title_i18n, lang)
        cards.append(card)

    facets_data = None
    if include_facets:
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
# PDP — Product detail
# ---------------------------------------------------------------------------


@storefront_products_router.get(
    path="/{slug}",
    status_code=status.HTTP_200_OK,
    response_model=StorefrontProductDetailResponse,
    summary="Get product detail for storefront (PDP)",
    description=(
        "Returns the full product detail for a published product identified by "
        "its slug.  Includes media gallery, variants with SKUs, attribute table, "
        "breadcrumbs, and a version field for ETag-based conditional requests."
    ),
)
async def get_storefront_product(
    slug: str,
    handler: FromDishka[GetStorefrontProductHandler],
    response: Response,
    lang: str | None = Query(
        None,
        min_length=2,
        max_length=5,
        description="Locale code for i18n projection (e.g. 'ru', 'en')",
    ),
) -> StorefrontProductDetailResponse:
    detail = await handler.handle(slug)

    response.headers["Cache-Control"] = _pdp_cache_control(lang)
    response.headers["ETag"] = f'W/"{detail.version}"'

    pdp = StorefrontProductDetailResponse.model_validate(detail, from_attributes=True)
    if lang:
        pdp.title = _project_i18n(pdp.title_i18n, lang)
        pdp.description = _project_i18n(pdp.description_i18n, lang)
        for bc in pdp.breadcrumbs:
            bc.label = _project_i18n(bc.label_i18n, lang)
        for v in pdp.variants:
            v.name = _project_i18n(v.name_i18n, lang)
        for a in pdp.attributes:
            a.attribute_name = _project_i18n(a.attribute_name_i18n, lang)
            a.value = _project_i18n(a.value_i18n, lang)
            if a.group_name_i18n:
                a.group_name = _project_i18n(a.group_name_i18n, lang)

    return pdp
