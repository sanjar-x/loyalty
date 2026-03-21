"""Dishka IoC providers for the Geo bounded context.

Registers repository implementations and query handlers into the
request-scoped DI container.
"""

from dishka import Provider, Scope, provide
from dishka.dependency_source.composite import CompositeDependencySource

from src.modules.geo.application.queries.list_countries import (
    ListCountriesHandler,
)
from src.modules.geo.application.queries.list_languages import (
    ListLanguagesHandler,
)
from src.modules.geo.application.queries.list_subdivisions import (
    ListSubdivisionsHandler,
)
from src.modules.geo.domain.interfaces import (
    ICountryRepository,
    ILanguageRepository,
    ISubdivisionRepository,
)
from src.modules.geo.infrastructure.repositories.country import (
    CountryRepository,
)
from src.modules.geo.infrastructure.repositories.language import (
    LanguageRepository,
)
from src.modules.geo.infrastructure.repositories.subdivision import (
    SubdivisionRepository,
)


class GeoProvider(Provider):
    """DI provider for geo repositories and query handlers."""

    country_repo: CompositeDependencySource = provide(
        CountryRepository, scope=Scope.REQUEST, provides=ICountryRepository,
    )
    language_repo: CompositeDependencySource = provide(
        LanguageRepository, scope=Scope.REQUEST, provides=ILanguageRepository,
    )
    subdivision_repo: CompositeDependencySource = provide(
        SubdivisionRepository, scope=Scope.REQUEST, provides=ISubdivisionRepository,
    )
    list_countries_handler: CompositeDependencySource = provide(
        ListCountriesHandler, scope=Scope.REQUEST,
    )
    list_languages_handler: CompositeDependencySource = provide(
        ListLanguagesHandler, scope=Scope.REQUEST,
    )
    list_subdivisions_handler: CompositeDependencySource = provide(
        ListSubdivisionsHandler, scope=Scope.REQUEST,
    )
