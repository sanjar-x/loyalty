"""
FastAPI router for the homepage «Для вас» (For You) feed.

Public, optionally-authenticated endpoint.  When the caller presents a valid
JWT we read their activity history and return a personalized list ordered by
category affinity + global trending diversity.  Anonymous callers receive
the cold-start fallback (Redis weekly trending, then popularity_score).

Strategy versioning is embedded in the cursor so clients can keep scrolling
a consistent materialised list while we roll out new ranking algorithms
behind the scenes.

URL path (under ``/api/v1/catalog``):

* ``GET /storefront/for-you`` — paginated personalized feed
"""

from __future__ import annotations

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Query, Request, Response
from pydantic import BaseModel, Field

from src.modules.catalog.application.queries.get_for_you_feed import (
    ForYouFeedHandler,
    ForYouFeedQuery,
    ForYouFeedResult,
)
from src.modules.catalog.presentation.router_storefront_products import (
    _extract_identity_id,
    _project_i18n,
)
from src.modules.catalog.presentation.schemas_storefront import (
    StorefrontProductCardResponse,
)
from src.shared.interfaces.security import ITokenProvider

storefront_for_you_router = APIRouter(
    prefix="/storefront/for-you",
    tags=["Storefront For You"],
    route_class=DishkaRoute,
)


# Short cache is safe: candidate lists are stable for the cursor's seed
# anyway, and per-user personalization is best served fresh.
_FOR_YOU_CACHE_CONTROL = "private, max-age=60, stale-while-revalidate=120"


class ForYouFeedResponse(BaseModel):
    items: list[StorefrontProductCardResponse]
    next_cursor: str | None = Field(
        default=None,
        description="Opaque pagination token. Pass back in ``cursor`` query param.",
    )
    strategy_version: str = Field(
        ..., description="Ranking strategy version used to build this feed."
    )
    is_personalized: bool = Field(
        ...,
        description=(
            "True when the list was ranked using the caller's activity "
            "history.  False means the caller is anonymous or too new — "
            "the response is a cold-start fallback."
        ),
    )


@storefront_for_you_router.get(
    "",
    response_model=ForYouFeedResponse,
    summary="Personalized «Для вас» feed",
    description=(
        "Returns a cursor-paginated list of product cards ranked for the "
        "caller.  Authenticated users with >=5 activity events in the past "
        "30 days get a personalized feed based on their category affinities; "
        "everyone else receives the cold-start fallback (weekly trending + "
        "popular products).  Pagination uses an opaque cursor — keep passing "
        "back ``next_cursor`` until the server returns ``null``."
    ),
)
async def get_for_you_feed(
    request: Request,
    handler: FromDishka[ForYouFeedHandler],
    token_provider: FromDishka[ITokenProvider],
    response: Response,
    limit: int = Query(20, ge=1, le=50, description="Page size"),
    cursor: str | None = Query(
        None, description="Opaque pagination token from a prior response."
    ),
    lang: str | None = Query(
        None, pattern=r"^(ru|en)$", description="Language for title projection"
    ),
) -> ForYouFeedResponse:
    identity_str = _extract_identity_id(request, token_provider)
    user_id = None
    if identity_str:
        try:
            import uuid as _uuid

            user_id = _uuid.UUID(identity_str)
        except ValueError:
            user_id = None

    result: ForYouFeedResult = await handler.handle(
        ForYouFeedQuery(user_id=user_id, limit=limit, cursor=cursor)
    )

    items: list[StorefrontProductCardResponse] = []
    for card in result.items:
        item = StorefrontProductCardResponse.model_validate(card, from_attributes=True)
        if lang:
            item.title = _project_i18n(item.title_i18n, lang)
            for opt in item.variant_options:
                opt.attribute_name = _project_i18n(opt.attribute_name_i18n, lang)
                for ov in opt.values:
                    ov.value = _project_i18n(ov.value_i18n, lang)
        items.append(item)

    response.headers["Cache-Control"] = _FOR_YOU_CACHE_CONTROL

    return ForYouFeedResponse(
        items=items,
        next_cursor=result.next_cursor,
        strategy_version=result.strategy_version,
        is_personalized=result.is_personalized,
    )
