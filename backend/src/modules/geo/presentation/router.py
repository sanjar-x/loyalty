"""FastAPI router for geo reference-data endpoints.

Public read-only endpoints for countries, languages, and subdivisions.
No authentication required — reference data is public.
"""

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Query

from src.modules.geo.application.queries.list_countries import (
    ListCountriesHandler,
)
from src.modules.geo.application.queries.list_languages import (
    ListLanguagesHandler,
)
from src.modules.geo.application.queries.list_subdivisions import (
    ListSubdivisionsHandler,
)
from src.modules.geo.application.queries.read_models import (
    CountryListReadModel,
    LanguageListReadModel,
    SubdivisionListReadModel,
)

geo_router = APIRouter(
    prefix="/geo",
    tags=["Geo"],
    route_class=DishkaRoute,
)


@geo_router.get("/countries")
async def list_countries(
    handler: FromDishka[ListCountriesHandler],
    lang: str | None = Query(None, description="Filter translations to this language code"),
) -> CountryListReadModel:
    """List all countries with optional language filter for translations."""
    return await handler.handle(lang_code=lang)


@geo_router.get("/languages")
async def list_languages(
    handler: FromDishka[ListLanguagesHandler],
    include_inactive: bool = Query(False, description="Include inactive languages"),
) -> LanguageListReadModel:
    """List languages (active by default, or all if include_inactive=true)."""
    return await handler.handle(include_inactive=include_inactive)


@geo_router.get("/countries/{country_code}/subdivisions")
async def list_subdivisions(
    country_code: str,
    handler: FromDishka[ListSubdivisionsHandler],
    lang: str | None = Query(None, description="Filter translations to this language code"),
) -> SubdivisionListReadModel:
    """List subdivisions for a country."""
    return await handler.handle(country_code=country_code, lang_code=lang)
