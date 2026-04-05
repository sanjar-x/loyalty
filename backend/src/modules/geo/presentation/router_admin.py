"""FastAPI admin router for geo reference-data management.

All endpoints require ``geo:manage`` permission.
"""

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Depends, Query, status

from src.modules.geo.application.commands.manage_countries import (
    CountryCurrencyLinkItem,
    CountryTranslationItem,
    CreateCountryCommand,
    CreateCountryHandler,
    DeleteCountryHandler,
    SetCountryCurrenciesCommand,
    SetCountryCurrenciesHandler,
    UpdateCountryCommand,
    UpdateCountryHandler,
    UpsertCountryTranslationsCommand,
    UpsertCountryTranslationsHandler,
)
from src.modules.geo.application.commands.manage_currencies import (
    CreateCurrencyCommand,
    CreateCurrencyHandler,
    CurrencyTranslationItem,
    DeleteCurrencyHandler,
    UpdateCurrencyCommand,
    UpdateCurrencyHandler,
    UpsertCurrencyTranslationsCommand,
    UpsertCurrencyTranslationsHandler,
)
from src.modules.geo.application.commands.manage_languages import (
    CreateLanguageCommand,
    CreateLanguageHandler,
    DeleteLanguageHandler,
    UpdateLanguageCommand,
    UpdateLanguageHandler,
)
from src.modules.geo.application.commands.manage_subdivisions import (
    CreateSubdivisionCategoryCommand,
    CreateSubdivisionCategoryHandler,
    CreateSubdivisionCommand,
    CreateSubdivisionHandler,
    DeleteSubdivisionCategoryHandler,
    DeleteSubdivisionHandler,
    ListSubdivisionCategoriesHandler,
    SubdivisionCategoryTranslationItem,
    SubdivisionTranslationItem,
    UpdateSubdivisionCategoryCommand,
    UpdateSubdivisionCategoryHandler,
    UpdateSubdivisionCommand,
    UpdateSubdivisionHandler,
    UpsertSubdivisionCategoryTranslationsCommand,
    UpsertSubdivisionCategoryTranslationsHandler,
    UpsertSubdivisionTranslationsCommand,
    UpsertSubdivisionTranslationsHandler,
)
from src.modules.geo.application.queries.read_models import (
    CountryCurrencyLinkReadModel,
    CountryReadModel,
    CountryTranslationReadModel,
    CurrencyReadModel,
    CurrencyTranslationReadModel,
    LanguageReadModel,
    SubdivisionCategoryListReadModel,
    SubdivisionCategoryReadModel,
    SubdivisionCategoryTranslationReadModel,
    SubdivisionReadModel,
    SubdivisionTranslationReadModel,
)
from src.modules.geo.presentation.schemas import (
    CreateCountryRequest,
    CreateCurrencyRequest,
    CreateLanguageRequest,
    CreateSubdivisionCategoryRequest,
    CreateSubdivisionRequest,
    SetCountryCurrenciesRequest,
    UpdateCountryRequest,
    UpdateCurrencyRequest,
    UpdateLanguageRequest,
    UpdateSubdivisionCategoryRequest,
    UpdateSubdivisionRequest,
    UpsertCountryTranslationsRequest,
    UpsertCurrencyTranslationsRequest,
    UpsertSubdivisionCategoryTranslationsRequest,
    UpsertSubdivisionTranslationsRequest,
)
from src.modules.identity.presentation.dependencies import RequirePermission

_GEO_MANAGE = [Depends(RequirePermission("geo:manage"))]

geo_admin_router = APIRouter(
    prefix="/admin/geo",
    tags=["Geo Admin"],
    route_class=DishkaRoute,
    dependencies=_GEO_MANAGE,
)


# ===================================================================
#  Countries
# ===================================================================


@geo_admin_router.post(
    "/countries",
    status_code=status.HTTP_201_CREATED,
    response_model=CountryReadModel,
    summary="Create a country",
)
async def create_country(
    request: CreateCountryRequest,
    handler: FromDishka[CreateCountryHandler],
) -> CountryReadModel:
    command = CreateCountryCommand(
        alpha2=request.alpha2,
        alpha3=request.alpha3,
        numeric=request.numeric,
    )
    return await handler.handle(command)


@geo_admin_router.patch(
    "/countries/{alpha2}",
    response_model=CountryReadModel,
    summary="Update a country",
)
async def update_country(
    alpha2: str,
    request: UpdateCountryRequest,
    handler: FromDishka[UpdateCountryHandler],
) -> CountryReadModel:
    command = UpdateCountryCommand(
        alpha2=alpha2.upper(),
        alpha3=request.alpha3,
        numeric=request.numeric,
        _provided_fields=frozenset(request.model_fields_set),
    )
    return await handler.handle(command)


@geo_admin_router.delete(
    "/countries/{alpha2}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a country",
)
async def delete_country(
    alpha2: str,
    handler: FromDishka[DeleteCountryHandler],
) -> None:
    await handler.handle(alpha2.upper())


@geo_admin_router.put(
    "/countries/{alpha2}/translations",
    response_model=list[CountryTranslationReadModel],
    summary="Upsert country translations",
)
async def upsert_country_translations(
    alpha2: str,
    request: UpsertCountryTranslationsRequest,
    handler: FromDishka[UpsertCountryTranslationsHandler],
) -> list[CountryTranslationReadModel]:
    command = UpsertCountryTranslationsCommand(
        alpha2=alpha2.upper(),
        translations=[
            CountryTranslationItem(
                lang_code=t.lang_code,
                name=t.name,
                official_name=t.official_name,
            )
            for t in request.translations
        ],
    )
    return await handler.handle(command)


@geo_admin_router.put(
    "/countries/{alpha2}/currencies",
    response_model=list[CountryCurrencyLinkReadModel],
    summary="Set country-currency links",
)
async def set_country_currencies(
    alpha2: str,
    request: SetCountryCurrenciesRequest,
    handler: FromDishka[SetCountryCurrenciesHandler],
) -> list[CountryCurrencyLinkReadModel]:
    command = SetCountryCurrenciesCommand(
        alpha2=alpha2.upper(),
        currencies=[
            CountryCurrencyLinkItem(
                currency_code=c.currency_code,
                is_primary=c.is_primary,
            )
            for c in request.currencies
        ],
    )
    return await handler.handle(command)


# ===================================================================
#  Currencies
# ===================================================================


@geo_admin_router.post(
    "/currencies",
    status_code=status.HTTP_201_CREATED,
    response_model=CurrencyReadModel,
    summary="Create a currency",
)
async def create_currency(
    request: CreateCurrencyRequest,
    handler: FromDishka[CreateCurrencyHandler],
) -> CurrencyReadModel:
    command = CreateCurrencyCommand(
        code=request.code,
        numeric=request.numeric,
        name=request.name,
        minor_unit=request.minor_unit,
        is_active=request.is_active,
        sort_order=request.sort_order,
    )
    return await handler.handle(command)


@geo_admin_router.patch(
    "/currencies/{code}",
    response_model=CurrencyReadModel,
    summary="Update a currency",
)
async def update_currency(
    code: str,
    request: UpdateCurrencyRequest,
    handler: FromDishka[UpdateCurrencyHandler],
) -> CurrencyReadModel:
    command = UpdateCurrencyCommand(
        code=code.upper(),
        numeric=request.numeric,
        name=request.name,
        minor_unit=request.minor_unit,
        is_active=request.is_active,
        sort_order=request.sort_order,
        _provided_fields=frozenset(request.model_fields_set),
    )
    return await handler.handle(command)


@geo_admin_router.delete(
    "/currencies/{code}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a currency",
)
async def delete_currency(
    code: str,
    handler: FromDishka[DeleteCurrencyHandler],
) -> None:
    await handler.handle(code.upper())


@geo_admin_router.put(
    "/currencies/{code}/translations",
    response_model=list[CurrencyTranslationReadModel],
    summary="Upsert currency translations",
)
async def upsert_currency_translations(
    code: str,
    request: UpsertCurrencyTranslationsRequest,
    handler: FromDishka[UpsertCurrencyTranslationsHandler],
) -> list[CurrencyTranslationReadModel]:
    command = UpsertCurrencyTranslationsCommand(
        code=code.upper(),
        translations=[
            CurrencyTranslationItem(lang_code=t.lang_code, name=t.name)
            for t in request.translations
        ],
    )
    return await handler.handle(command)


# ===================================================================
#  Languages
# ===================================================================


@geo_admin_router.post(
    "/languages",
    status_code=status.HTTP_201_CREATED,
    response_model=LanguageReadModel,
    summary="Create a language",
)
async def create_language(
    request: CreateLanguageRequest,
    handler: FromDishka[CreateLanguageHandler],
) -> LanguageReadModel:
    command = CreateLanguageCommand(
        code=request.code,
        iso639_1=request.iso639_1,
        iso639_2=request.iso639_2,
        iso639_3=request.iso639_3,
        script=request.script,
        name_en=request.name_en,
        name_native=request.name_native,
        direction=request.direction,
        is_active=request.is_active,
        is_default=request.is_default,
        sort_order=request.sort_order,
    )
    return await handler.handle(command)


@geo_admin_router.patch(
    "/languages/{code}",
    response_model=LanguageReadModel,
    summary="Update a language",
)
async def update_language(
    code: str,
    request: UpdateLanguageRequest,
    handler: FromDishka[UpdateLanguageHandler],
) -> LanguageReadModel:
    command = UpdateLanguageCommand(
        code=code,
        iso639_1=request.iso639_1,
        iso639_2=request.iso639_2,
        iso639_3=request.iso639_3,
        script=request.script,
        name_en=request.name_en,
        name_native=request.name_native,
        direction=request.direction,
        is_active=request.is_active,
        is_default=request.is_default,
        sort_order=request.sort_order,
        _provided_fields=frozenset(request.model_fields_set),
    )
    return await handler.handle(command)


@geo_admin_router.delete(
    "/languages/{code}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a language",
)
async def delete_language(
    code: str,
    handler: FromDishka[DeleteLanguageHandler],
) -> None:
    await handler.handle(code)


# ===================================================================
#  Subdivisions
# ===================================================================


@geo_admin_router.post(
    "/subdivisions",
    status_code=status.HTTP_201_CREATED,
    response_model=SubdivisionReadModel,
    summary="Create a subdivision",
)
async def create_subdivision(
    request: CreateSubdivisionRequest,
    handler: FromDishka[CreateSubdivisionHandler],
) -> SubdivisionReadModel:
    command = CreateSubdivisionCommand(
        code=request.code,
        country_code=request.country_code,
        category_code=request.category_code,
        parent_code=request.parent_code,
        latitude=request.latitude,
        longitude=request.longitude,
        sort_order=request.sort_order,
        is_active=request.is_active,
    )
    return await handler.handle(command)


@geo_admin_router.patch(
    "/subdivisions/{code}",
    response_model=SubdivisionReadModel,
    summary="Update a subdivision",
)
async def update_subdivision(
    code: str,
    request: UpdateSubdivisionRequest,
    handler: FromDishka[UpdateSubdivisionHandler],
) -> SubdivisionReadModel:
    command = UpdateSubdivisionCommand(
        code=code.upper(),
        category_code=request.category_code,
        parent_code=request.parent_code,
        latitude=request.latitude,
        longitude=request.longitude,
        sort_order=request.sort_order,
        is_active=request.is_active,
        _provided_fields=frozenset(request.model_fields_set),
    )
    return await handler.handle(command)


@geo_admin_router.delete(
    "/subdivisions/{code}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a subdivision",
)
async def delete_subdivision(
    code: str,
    handler: FromDishka[DeleteSubdivisionHandler],
) -> None:
    await handler.handle(code.upper())


@geo_admin_router.put(
    "/subdivisions/{code}/translations",
    response_model=list[SubdivisionTranslationReadModel],
    summary="Upsert subdivision translations",
)
async def upsert_subdivision_translations(
    code: str,
    request: UpsertSubdivisionTranslationsRequest,
    handler: FromDishka[UpsertSubdivisionTranslationsHandler],
) -> list[SubdivisionTranslationReadModel]:
    command = UpsertSubdivisionTranslationsCommand(
        code=code.upper(),
        translations=[
            SubdivisionTranslationItem(
                lang_code=t.lang_code,
                name=t.name,
                official_name=t.official_name,
                local_variant=t.local_variant,
            )
            for t in request.translations
        ],
    )
    return await handler.handle(command)


# ===================================================================
#  Subdivision Categories
# ===================================================================


@geo_admin_router.get(
    "/subdivision-categories",
    response_model=SubdivisionCategoryListReadModel,
    summary="List subdivision categories",
)
async def list_subdivision_categories(
    handler: FromDishka[ListSubdivisionCategoriesHandler],
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> SubdivisionCategoryListReadModel:
    return await handler.handle(offset=offset, limit=limit)


@geo_admin_router.post(
    "/subdivision-categories",
    status_code=status.HTTP_201_CREATED,
    response_model=SubdivisionCategoryReadModel,
    summary="Create a subdivision category",
)
async def create_subdivision_category(
    request: CreateSubdivisionCategoryRequest,
    handler: FromDishka[CreateSubdivisionCategoryHandler],
) -> SubdivisionCategoryReadModel:
    command = CreateSubdivisionCategoryCommand(
        code=request.code,
        sort_order=request.sort_order,
    )
    return await handler.handle(command)


@geo_admin_router.patch(
    "/subdivision-categories/{code}",
    response_model=SubdivisionCategoryReadModel,
    summary="Update a subdivision category",
)
async def update_subdivision_category(
    code: str,
    request: UpdateSubdivisionCategoryRequest,
    handler: FromDishka[UpdateSubdivisionCategoryHandler],
) -> SubdivisionCategoryReadModel:
    command = UpdateSubdivisionCategoryCommand(
        code=code,
        sort_order=request.sort_order,
        _provided_fields=frozenset(request.model_fields_set),
    )
    return await handler.handle(command)


@geo_admin_router.delete(
    "/subdivision-categories/{code}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a subdivision category",
)
async def delete_subdivision_category(
    code: str,
    handler: FromDishka[DeleteSubdivisionCategoryHandler],
) -> None:
    await handler.handle(code)


@geo_admin_router.put(
    "/subdivision-categories/{code}/translations",
    response_model=list[SubdivisionCategoryTranslationReadModel],
    summary="Upsert subdivision category translations",
)
async def upsert_subdivision_category_translations(
    code: str,
    request: UpsertSubdivisionCategoryTranslationsRequest,
    handler: FromDishka[UpsertSubdivisionCategoryTranslationsHandler],
) -> list[SubdivisionCategoryTranslationReadModel]:
    command = UpsertSubdivisionCategoryTranslationsCommand(
        code=code,
        translations=[
            SubdivisionCategoryTranslationItem(lang_code=t.lang_code, name=t.name)
            for t in request.translations
        ],
    )
    return await handler.handle(command)
