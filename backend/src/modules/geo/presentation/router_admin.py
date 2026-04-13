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
from src.modules.geo.application.commands.manage_districts import (
    CreateDistrictCommand,
    CreateDistrictHandler,
    CreateDistrictTypeCommand,
    CreateDistrictTypeHandler,
    DeleteDistrictHandler,
    DeleteDistrictTypeHandler,
    DistrictTranslationItem,
    DistrictTypeTranslationItem,
    ListDistrictTypesHandler,
    UpdateDistrictCommand,
    UpdateDistrictHandler,
    UpdateDistrictTypeCommand,
    UpdateDistrictTypeHandler,
    UpsertDistrictTranslationsCommand,
    UpsertDistrictTranslationsHandler,
    UpsertDistrictTypeTranslationsCommand,
    UpsertDistrictTypeTranslationsHandler,
)
from src.modules.geo.application.commands.manage_languages import (
    CreateLanguageCommand,
    CreateLanguageHandler,
    DeleteLanguageHandler,
    UpdateLanguageCommand,
    UpdateLanguageHandler,
)
from src.modules.geo.application.commands.manage_subdivisions import (
    CreateSubdivisionCommand,
    CreateSubdivisionHandler,
    CreateSubdivisionTypeCommand,
    CreateSubdivisionTypeHandler,
    DeleteSubdivisionHandler,
    DeleteSubdivisionTypeHandler,
    ListSubdivisionTypesHandler,
    SubdivisionTranslationItem,
    SubdivisionTypeTranslationItem,
    UpdateSubdivisionCommand,
    UpdateSubdivisionHandler,
    UpdateSubdivisionTypeCommand,
    UpdateSubdivisionTypeHandler,
    UpsertSubdivisionTranslationsCommand,
    UpsertSubdivisionTranslationsHandler,
    UpsertSubdivisionTypeTranslationsCommand,
    UpsertSubdivisionTypeTranslationsHandler,
)
from src.modules.geo.application.queries.read_models import (
    CountryCurrencyLinkReadModel,
    CountryReadModel,
    CountryTranslationReadModel,
    CurrencyReadModel,
    CurrencyTranslationReadModel,
    DistrictReadModel,
    DistrictTranslationReadModel,
    DistrictTypeListReadModel,
    DistrictTypeReadModel,
    DistrictTypeTranslationReadModel,
    LanguageReadModel,
    SubdivisionReadModel,
    SubdivisionTranslationReadModel,
    SubdivisionTypeListReadModel,
    SubdivisionTypeReadModel,
    SubdivisionTypeTranslationReadModel,
)
from src.modules.geo.presentation.schemas import (
    CreateCountryRequest,
    CreateCurrencyRequest,
    CreateDistrictRequest,
    CreateDistrictTypeRequest,
    CreateLanguageRequest,
    CreateSubdivisionRequest,
    CreateSubdivisionTypeRequest,
    SetCountryCurrenciesRequest,
    UpdateCountryRequest,
    UpdateCurrencyRequest,
    UpdateDistrictRequest,
    UpdateDistrictTypeRequest,
    UpdateLanguageRequest,
    UpdateSubdivisionRequest,
    UpdateSubdivisionTypeRequest,
    UpsertCountryTranslationsRequest,
    UpsertCurrencyTranslationsRequest,
    UpsertDistrictTranslationsRequest,
    UpsertDistrictTypeTranslationsRequest,
    UpsertSubdivisionTranslationsRequest,
    UpsertSubdivisionTypeTranslationsRequest,
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
        type_code=request.type_code,
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
        type_code=request.type_code,
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
    "/subdivision-types",
    response_model=SubdivisionTypeListReadModel,
    summary="List subdivision types",
)
async def list_subdivision_types(
    handler: FromDishka[ListSubdivisionTypesHandler],
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> SubdivisionTypeListReadModel:
    return await handler.handle(offset=offset, limit=limit)


@geo_admin_router.post(
    "/subdivision-types",
    status_code=status.HTTP_201_CREATED,
    response_model=SubdivisionTypeReadModel,
    summary="Create a subdivision type",
)
async def create_subdivision_type(
    request: CreateSubdivisionTypeRequest,
    handler: FromDishka[CreateSubdivisionTypeHandler],
) -> SubdivisionTypeReadModel:
    command = CreateSubdivisionTypeCommand(
        code=request.code,
        sort_order=request.sort_order,
    )
    return await handler.handle(command)


@geo_admin_router.patch(
    "/subdivision-types/{code}",
    response_model=SubdivisionTypeReadModel,
    summary="Update a subdivision type",
)
async def update_subdivision_type(
    code: str,
    request: UpdateSubdivisionTypeRequest,
    handler: FromDishka[UpdateSubdivisionTypeHandler],
) -> SubdivisionTypeReadModel:
    command = UpdateSubdivisionTypeCommand(
        code=code,
        sort_order=request.sort_order,
        _provided_fields=frozenset(request.model_fields_set),
    )
    return await handler.handle(command)


@geo_admin_router.delete(
    "/subdivision-types/{code}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a subdivision type",
)
async def delete_subdivision_type(
    code: str,
    handler: FromDishka[DeleteSubdivisionTypeHandler],
) -> None:
    await handler.handle(code)


@geo_admin_router.put(
    "/subdivision-types/{code}/translations",
    response_model=list[SubdivisionTypeTranslationReadModel],
    summary="Upsert subdivision type translations",
)
async def upsert_subdivision_type_translations(
    code: str,
    request: UpsertSubdivisionTypeTranslationsRequest,
    handler: FromDishka[UpsertSubdivisionTypeTranslationsHandler],
) -> list[SubdivisionTypeTranslationReadModel]:
    command = UpsertSubdivisionTypeTranslationsCommand(
        code=code,
        translations=[
            SubdivisionTypeTranslationItem(lang_code=t.lang_code, name=t.name)
            for t in request.translations
        ],
    )
    return await handler.handle(command)


# ===================================================================
#  Districts
# ===================================================================


@geo_admin_router.post(
    "/districts",
    status_code=status.HTTP_201_CREATED,
    response_model=DistrictReadModel,
    summary="Create a district",
)
async def create_district(
    request: CreateDistrictRequest,
    handler: FromDishka[CreateDistrictHandler],
) -> DistrictReadModel:
    command = CreateDistrictCommand(
        subdivision_code=request.subdivision_code,
        type_code=request.type_code,
        oktmo_prefix=request.oktmo_prefix,
        fias_guid=request.fias_guid,
        latitude=request.latitude,
        longitude=request.longitude,
        sort_order=request.sort_order,
        is_active=request.is_active,
    )
    return await handler.handle(command)


@geo_admin_router.patch(
    "/districts/{district_id}",
    response_model=DistrictReadModel,
    summary="Update a district",
)
async def update_district(
    district_id: str,
    request: UpdateDistrictRequest,
    handler: FromDishka[UpdateDistrictHandler],
) -> DistrictReadModel:
    command = UpdateDistrictCommand(
        district_id=district_id,
        type_code=request.type_code,
        oktmo_prefix=request.oktmo_prefix,
        fias_guid=request.fias_guid,
        latitude=request.latitude,
        longitude=request.longitude,
        sort_order=request.sort_order,
        is_active=request.is_active,
        _provided_fields=frozenset(request.model_fields_set),
    )
    return await handler.handle(command)


@geo_admin_router.delete(
    "/districts/{district_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a district",
)
async def delete_district(
    district_id: str,
    handler: FromDishka[DeleteDistrictHandler],
) -> None:
    await handler.handle(district_id)


@geo_admin_router.put(
    "/districts/{district_id}/translations",
    response_model=list[DistrictTranslationReadModel],
    summary="Upsert district translations",
)
async def upsert_district_translations(
    district_id: str,
    request: UpsertDistrictTranslationsRequest,
    handler: FromDishka[UpsertDistrictTranslationsHandler],
) -> list[DistrictTranslationReadModel]:
    command = UpsertDistrictTranslationsCommand(
        district_id=district_id,
        translations=[
            DistrictTranslationItem(
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
#  District Types
# ===================================================================


@geo_admin_router.get(
    "/district-types",
    response_model=DistrictTypeListReadModel,
    summary="List district types",
)
async def list_district_types(
    handler: FromDishka[ListDistrictTypesHandler],
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> DistrictTypeListReadModel:
    return await handler.handle(offset=offset, limit=limit)


@geo_admin_router.post(
    "/district-types",
    status_code=status.HTTP_201_CREATED,
    response_model=DistrictTypeReadModel,
    summary="Create a district type",
)
async def create_district_type(
    request: CreateDistrictTypeRequest,
    handler: FromDishka[CreateDistrictTypeHandler],
) -> DistrictTypeReadModel:
    command = CreateDistrictTypeCommand(
        code=request.code,
        sort_order=request.sort_order,
    )
    return await handler.handle(command)


@geo_admin_router.patch(
    "/district-types/{code}",
    response_model=DistrictTypeReadModel,
    summary="Update a district type",
)
async def update_district_type(
    code: str,
    request: UpdateDistrictTypeRequest,
    handler: FromDishka[UpdateDistrictTypeHandler],
) -> DistrictTypeReadModel:
    command = UpdateDistrictTypeCommand(
        code=code,
        sort_order=request.sort_order,
        _provided_fields=frozenset(request.model_fields_set),
    )
    return await handler.handle(command)


@geo_admin_router.delete(
    "/district-types/{code}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a district type",
)
async def delete_district_type(
    code: str,
    handler: FromDishka[DeleteDistrictTypeHandler],
) -> None:
    await handler.handle(code)


@geo_admin_router.put(
    "/district-types/{code}/translations",
    response_model=list[DistrictTypeTranslationReadModel],
    summary="Upsert district type translations",
)
async def upsert_district_type_translations(
    code: str,
    request: UpsertDistrictTypeTranslationsRequest,
    handler: FromDishka[UpsertDistrictTypeTranslationsHandler],
) -> list[DistrictTypeTranslationReadModel]:
    command = UpsertDistrictTypeTranslationsCommand(
        code=code,
        translations=[
            DistrictTypeTranslationItem(lang_code=t.lang_code, name=t.name)
            for t in request.translations
        ],
    )
    return await handler.handle(command)
