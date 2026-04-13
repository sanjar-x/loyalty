"""Dishka IoC providers for the Geo bounded context.

Registers repository implementations, query handlers, and admin command
handlers into the request-scoped DI container.
"""

from dishka import Provider, Scope, provide
from dishka.dependency_source.composite import CompositeDependencySource

from src.modules.geo.application.commands.manage_countries import (
    CreateCountryHandler,
    DeleteCountryHandler,
    SetCountryCurrenciesHandler,
    UpdateCountryHandler,
    UpsertCountryTranslationsHandler,
)
from src.modules.geo.application.commands.manage_currencies import (
    CreateCurrencyHandler,
    DeleteCurrencyHandler,
    UpdateCurrencyHandler,
    UpsertCurrencyTranslationsHandler,
)
from src.modules.geo.application.commands.manage_districts import (
    CreateDistrictHandler,
    CreateDistrictTypeHandler,
    DeleteDistrictHandler,
    DeleteDistrictTypeHandler,
    ListDistrictTypesHandler,
    UpdateDistrictHandler,
    UpdateDistrictTypeHandler,
    UpsertDistrictTranslationsHandler,
    UpsertDistrictTypeTranslationsHandler,
)
from src.modules.geo.application.commands.manage_languages import (
    CreateLanguageHandler,
    DeleteLanguageHandler,
    UpdateLanguageHandler,
)
from src.modules.geo.application.commands.manage_subdivisions import (
    CreateSubdivisionHandler,
    CreateSubdivisionTypeHandler,
    DeleteSubdivisionHandler,
    DeleteSubdivisionTypeHandler,
    ListSubdivisionTypesHandler,
    UpdateSubdivisionHandler,
    UpdateSubdivisionTypeHandler,
    UpsertSubdivisionTranslationsHandler,
    UpsertSubdivisionTypeTranslationsHandler,
)
from src.modules.geo.application.queries.get_country import GetCountryHandler
from src.modules.geo.application.queries.get_currency import GetCurrencyHandler
from src.modules.geo.application.queries.get_district import (
    GetDistrictHandler,
)
from src.modules.geo.application.queries.get_language import GetLanguageHandler
from src.modules.geo.application.queries.get_subdivision import (
    GetSubdivisionHandler,
)
from src.modules.geo.application.queries.list_countries import (
    ListCountriesHandler,
)
from src.modules.geo.application.queries.list_currencies import (
    ListCurrenciesHandler,
)
from src.modules.geo.application.queries.list_districts import (
    ListDistrictsHandler,
)
from src.modules.geo.application.queries.list_languages import (
    ListLanguagesHandler,
)
from src.modules.geo.application.queries.list_subdivisions import (
    ListSubdivisionsHandler,
)
from src.modules.geo.domain.interfaces import (
    ICountryRepository,
    ICurrencyRepository,
    IDistrictRepository,
    ILanguageRepository,
    ISubdivisionRepository,
)
from src.modules.geo.infrastructure.repositories.country import (
    CountryRepository,
)
from src.modules.geo.infrastructure.repositories.currency import (
    CurrencyRepository,
)
from src.modules.geo.infrastructure.repositories.district import (
    DistrictRepository,
)
from src.modules.geo.infrastructure.repositories.language import (
    LanguageRepository,
)
from src.modules.geo.infrastructure.repositories.subdivision import (
    SubdivisionRepository,
)


class GeoProvider(Provider):
    """DI provider for geo repositories and query handlers."""

    # -- Repositories -------------------------------------------------- #

    country_repo: CompositeDependencySource = provide(
        CountryRepository,
        scope=Scope.REQUEST,
        provides=ICountryRepository,
    )
    currency_repo: CompositeDependencySource = provide(
        CurrencyRepository,
        scope=Scope.REQUEST,
        provides=ICurrencyRepository,
    )
    language_repo: CompositeDependencySource = provide(
        LanguageRepository,
        scope=Scope.REQUEST,
        provides=ILanguageRepository,
    )
    subdivision_repo: CompositeDependencySource = provide(
        SubdivisionRepository,
        scope=Scope.REQUEST,
        provides=ISubdivisionRepository,
    )
    district_repo: CompositeDependencySource = provide(
        DistrictRepository,
        scope=Scope.REQUEST,
        provides=IDistrictRepository,
    )

    # -- Query handlers ------------------------------------------------ #

    get_country_handler: CompositeDependencySource = provide(
        GetCountryHandler,
        scope=Scope.REQUEST,
    )
    get_currency_handler: CompositeDependencySource = provide(
        GetCurrencyHandler,
        scope=Scope.REQUEST,
    )
    get_language_handler: CompositeDependencySource = provide(
        GetLanguageHandler,
        scope=Scope.REQUEST,
    )
    get_subdivision_handler: CompositeDependencySource = provide(
        GetSubdivisionHandler,
        scope=Scope.REQUEST,
    )
    list_countries_handler: CompositeDependencySource = provide(
        ListCountriesHandler,
        scope=Scope.REQUEST,
    )
    list_currencies_handler: CompositeDependencySource = provide(
        ListCurrenciesHandler,
        scope=Scope.REQUEST,
    )
    list_languages_handler: CompositeDependencySource = provide(
        ListLanguagesHandler,
        scope=Scope.REQUEST,
    )
    list_subdivisions_handler: CompositeDependencySource = provide(
        ListSubdivisionsHandler,
        scope=Scope.REQUEST,
    )
    get_district_handler: CompositeDependencySource = provide(
        GetDistrictHandler,
        scope=Scope.REQUEST,
    )
    list_districts_handler: CompositeDependencySource = provide(
        ListDistrictsHandler,
        scope=Scope.REQUEST,
    )

    # -- Country command handlers -------------------------------------- #

    create_country_handler: CompositeDependencySource = provide(
        CreateCountryHandler,
        scope=Scope.REQUEST,
    )
    update_country_handler: CompositeDependencySource = provide(
        UpdateCountryHandler,
        scope=Scope.REQUEST,
    )
    delete_country_handler: CompositeDependencySource = provide(
        DeleteCountryHandler,
        scope=Scope.REQUEST,
    )
    upsert_country_translations_handler: CompositeDependencySource = provide(
        UpsertCountryTranslationsHandler,
        scope=Scope.REQUEST,
    )
    set_country_currencies_handler: CompositeDependencySource = provide(
        SetCountryCurrenciesHandler,
        scope=Scope.REQUEST,
    )

    # -- Currency command handlers ------------------------------------- #

    create_currency_handler: CompositeDependencySource = provide(
        CreateCurrencyHandler,
        scope=Scope.REQUEST,
    )
    update_currency_handler: CompositeDependencySource = provide(
        UpdateCurrencyHandler,
        scope=Scope.REQUEST,
    )
    delete_currency_handler: CompositeDependencySource = provide(
        DeleteCurrencyHandler,
        scope=Scope.REQUEST,
    )
    upsert_currency_translations_handler: CompositeDependencySource = provide(
        UpsertCurrencyTranslationsHandler,
        scope=Scope.REQUEST,
    )

    # -- Language command handlers ------------------------------------- #

    create_language_handler: CompositeDependencySource = provide(
        CreateLanguageHandler,
        scope=Scope.REQUEST,
    )
    update_language_handler: CompositeDependencySource = provide(
        UpdateLanguageHandler,
        scope=Scope.REQUEST,
    )
    delete_language_handler: CompositeDependencySource = provide(
        DeleteLanguageHandler,
        scope=Scope.REQUEST,
    )

    # -- Subdivision command handlers ---------------------------------- #

    create_subdivision_handler: CompositeDependencySource = provide(
        CreateSubdivisionHandler,
        scope=Scope.REQUEST,
    )
    update_subdivision_handler: CompositeDependencySource = provide(
        UpdateSubdivisionHandler,
        scope=Scope.REQUEST,
    )
    delete_subdivision_handler: CompositeDependencySource = provide(
        DeleteSubdivisionHandler,
        scope=Scope.REQUEST,
    )
    upsert_subdivision_translations_handler: CompositeDependencySource = provide(
        UpsertSubdivisionTranslationsHandler,
        scope=Scope.REQUEST,
    )

    # -- Subdivision type command handlers ------------------------- #

    list_subdivision_types_handler: CompositeDependencySource = provide(
        ListSubdivisionTypesHandler,
        scope=Scope.REQUEST,
    )
    create_subdivision_type_handler: CompositeDependencySource = provide(
        CreateSubdivisionTypeHandler,
        scope=Scope.REQUEST,
    )
    update_subdivision_type_handler: CompositeDependencySource = provide(
        UpdateSubdivisionTypeHandler,
        scope=Scope.REQUEST,
    )
    delete_subdivision_type_handler: CompositeDependencySource = provide(
        DeleteSubdivisionTypeHandler,
        scope=Scope.REQUEST,
    )
    upsert_subdivision_type_translations_handler: CompositeDependencySource = provide(
        UpsertSubdivisionTypeTranslationsHandler,
        scope=Scope.REQUEST,
    )

    # -- District command handlers ------------------------------------ #

    create_district_handler: CompositeDependencySource = provide(
        CreateDistrictHandler,
        scope=Scope.REQUEST,
    )
    update_district_handler: CompositeDependencySource = provide(
        UpdateDistrictHandler,
        scope=Scope.REQUEST,
    )
    delete_district_handler: CompositeDependencySource = provide(
        DeleteDistrictHandler,
        scope=Scope.REQUEST,
    )
    upsert_district_translations_handler: CompositeDependencySource = provide(
        UpsertDistrictTranslationsHandler,
        scope=Scope.REQUEST,
    )

    # -- District type command handlers ------------------------------- #

    list_district_types_handler: CompositeDependencySource = provide(
        ListDistrictTypesHandler,
        scope=Scope.REQUEST,
    )
    create_district_type_handler: CompositeDependencySource = provide(
        CreateDistrictTypeHandler,
        scope=Scope.REQUEST,
    )
    update_district_type_handler: CompositeDependencySource = provide(
        UpdateDistrictTypeHandler,
        scope=Scope.REQUEST,
    )
    delete_district_type_handler: CompositeDependencySource = provide(
        DeleteDistrictTypeHandler,
        scope=Scope.REQUEST,
    )
    upsert_district_type_translations_handler: CompositeDependencySource = provide(
        UpsertDistrictTypeTranslationsHandler,
        scope=Scope.REQUEST,
    )
