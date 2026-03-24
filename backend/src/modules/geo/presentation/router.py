"""FastAPI router for geo reference-data endpoints.

Public read-only endpoints for countries, languages, currencies,
and subdivisions.  No authentication required — reference data is public.
"""

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Query, Response

from src.modules.geo.application.queries.list_countries import (
    ListCountriesHandler,
)
from src.modules.geo.application.queries.list_currencies import (
    ListCurrenciesHandler,
)
from src.modules.geo.application.queries.list_languages import (
    ListLanguagesHandler,
)
from src.modules.geo.application.queries.list_subdivisions import (
    ListSubdivisionsHandler,
)
from src.modules.geo.application.queries.read_models import (
    CountryListReadModel,
    CurrencyListReadModel,
    LanguageListReadModel,
    SubdivisionListReadModel,
)

_CACHE_CONTROL = "public, max-age=3600"

geo_router = APIRouter(
    prefix="/geo",
    tags=["Geo"],
    route_class=DishkaRoute,
)


@geo_router.get(
    "/countries",
    response_model=CountryListReadModel,
    summary="List all countries with translations",
)
async def list_countries(
    response: Response,
    handler: FromDishka[ListCountriesHandler],
    lang: str | None = Query(
        None, description="Filter translations to this language code"
    ),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(50, ge=1, le=500, description="Pagination limit"),
) -> CountryListReadModel:
    """List all countries with optional language filter for translations."""
    result = await handler.handle(lang_code=lang, offset=offset, limit=limit)
    response.headers["Cache-Control"] = _CACHE_CONTROL
    return result


@geo_router.get(
    "/currencies",
    response_model=CurrencyListReadModel,
    summary="List currencies with translations",
)
async def list_currencies(
    response: Response,
    handler: FromDishka[ListCurrenciesHandler],
    lang: str | None = Query(
        None, description="Filter translations to this language code"
    ),
    include_inactive: bool = Query(False, description="Include inactive currencies"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(50, ge=1, le=500, description="Pagination limit"),
) -> CurrencyListReadModel:
    """List currencies (active by default) with optional language filter."""
    result = await handler.handle(
        lang_code=lang,
        include_inactive=include_inactive,
        offset=offset,
        limit=limit,
    )
    response.headers["Cache-Control"] = _CACHE_CONTROL
    return result


@geo_router.get(
    "/languages",
    response_model=LanguageListReadModel,
    summary="List supported languages",
)
async def list_languages(
    response: Response,
    handler: FromDishka[ListLanguagesHandler],
    include_inactive: bool = Query(False, description="Include inactive languages"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(50, ge=1, le=500, description="Pagination limit"),
) -> LanguageListReadModel:
    """List languages (active by default, or all if include_inactive=true)."""
    result = await handler.handle(
        include_inactive=include_inactive,
        offset=offset,
        limit=limit,
    )
    response.headers["Cache-Control"] = _CACHE_CONTROL
    return result


@geo_router.get(
    "/countries/{country_code}/currencies",
    response_model=CurrencyListReadModel,
    summary="List currencies for a country",
)
async def list_country_currencies(
    country_code: str,
    response: Response,
    handler: FromDishka[ListCurrenciesHandler],
    lang: str | None = Query(
        None, description="Filter translations to this language code"
    ),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(50, ge=1, le=500, description="Pagination limit"),
) -> CurrencyListReadModel:
    """List currencies used by a specific country (404 if country not found)."""
    result = await handler.handle(
        country_code=country_code,
        lang_code=lang,
        offset=offset,
        limit=limit,
    )
    response.headers["Cache-Control"] = _CACHE_CONTROL
    return result


@geo_router.get(
    "/countries/{country_code}/subdivisions",
    response_model=SubdivisionListReadModel,
    summary="List subdivisions for a country",
)
async def list_subdivisions(
    country_code: str,
    response: Response,
    handler: FromDishka[ListSubdivisionsHandler],
    lang: str | None = Query(
        None, description="Filter translations to this language code"
    ),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(50, ge=1, le=500, description="Pagination limit"),
) -> SubdivisionListReadModel:
    """List subdivisions for a country (404 if country not found)."""
    result = await handler.handle(
        country_code=country_code,
        lang_code=lang,
        offset=offset,
        limit=limit,
    )
    response.headers["Cache-Control"] = _CACHE_CONTROL
    return result
