"""Geo repository port interfaces.

Defines abstract repository contracts for Country, Language, and
Subdivision.  The application layer depends only on these interfaces;
concrete implementations live in the infrastructure layer.
"""

from abc import ABC, abstractmethod

from src.modules.geo.domain.value_objects import Country, Language, Subdivision


class ICountryRepository(ABC):
    """Read-only repository contract for country reference data."""

    @abstractmethod
    async def get_by_alpha2(self, alpha2: str) -> Country | None:
        """Retrieve a country by ISO 3166-1 Alpha-2 code."""

    @abstractmethod
    async def get_by_alpha3(self, alpha3: str) -> Country | None:
        """Retrieve a country by ISO 3166-1 Alpha-3 code."""

    @abstractmethod
    async def list_all(self) -> list[Country]:
        """Retrieve all countries ordered by English name."""


class ILanguageRepository(ABC):
    """Read-only repository contract for language reference data."""

    @abstractmethod
    async def get_by_code(self, code: str) -> Language | None:
        """Retrieve a language by its IETF BCP 47 code."""

    @abstractmethod
    async def list_active(self) -> list[Language]:
        """Retrieve active languages ordered by ``sort_order``."""

    @abstractmethod
    async def list_all(self) -> list[Language]:
        """Retrieve all languages (including inactive) ordered by ``sort_order``."""

    @abstractmethod
    async def get_default(self) -> Language | None:
        """Retrieve the default fallback language (``is_default=True``)."""


class ISubdivisionRepository(ABC):
    """Read-only repository contract for subdivision reference data."""

    @abstractmethod
    async def get_by_code(self, code: str) -> Subdivision | None:
        """Retrieve a subdivision by ISO 3166-2 code."""

    @abstractmethod
    async def list_by_country(self, country_code: str) -> list[Subdivision]:
        """Retrieve all active subdivisions for a country, ordered by ``sort_order``."""
