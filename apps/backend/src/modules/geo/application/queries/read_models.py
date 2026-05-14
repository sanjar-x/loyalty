"""Read models (DTOs) for Geo query handlers.

Flat projections for the CQRS read side.  Carry no business logic —
only data for API responses.
"""

from pydantic import Field

from src.shared.schemas import CamelModel

# ------------------------------------------------------------------ #
#  Country
# ------------------------------------------------------------------ #


class CountryTranslationReadModel(CamelModel):
    """Single translation row for a country."""

    lang_code: str
    name: str
    official_name: str | None = None


class CountryReadModel(CamelModel):
    """Country with inline translations."""

    alpha2: str
    alpha3: str
    numeric: str
    translations: list[CountryTranslationReadModel] = Field(default_factory=list)


class CountryListReadModel(CamelModel):
    """Full country list response."""

    items: list[CountryReadModel]
    total: int


# ------------------------------------------------------------------ #
#  Currency
# ------------------------------------------------------------------ #


class CurrencyTranslationReadModel(CamelModel):
    """Single translation row for a currency."""

    lang_code: str
    name: str


class CurrencyReadModel(CamelModel):
    """Currency with inline translations."""

    code: str
    numeric: str
    name: str
    minor_unit: int | None = None
    is_active: bool = True
    sort_order: int = 0
    translations: list[CurrencyTranslationReadModel] = Field(default_factory=list)


class CurrencyListReadModel(CamelModel):
    """Currency list response."""

    items: list[CurrencyReadModel]
    total: int


# ------------------------------------------------------------------ #
#  Language
# ------------------------------------------------------------------ #


class LanguageReadModel(CamelModel):
    """Language / locale read model."""

    code: str
    iso639_1: str | None = None
    iso639_2: str | None = None
    iso639_3: str | None = None
    script: str | None = None
    name_en: str
    name_native: str
    direction: str
    is_active: bool
    is_default: bool
    sort_order: int


class LanguageListReadModel(CamelModel):
    """Language list response."""

    items: list[LanguageReadModel]
    total: int


# ------------------------------------------------------------------ #
#  Subdivision
# ------------------------------------------------------------------ #


class SubdivisionTranslationReadModel(CamelModel):
    """Single translation row for a subdivision."""

    lang_code: str
    name: str
    official_name: str | None = None
    local_variant: str | None = None


class SubdivisionReadModel(CamelModel):
    """Subdivision with inline translations."""

    code: str
    country_code: str
    type_code: str
    parent_code: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    is_active: bool = True
    sort_order: int = 0
    translations: list[SubdivisionTranslationReadModel] = Field(default_factory=list)


class SubdivisionListReadModel(CamelModel):
    """Subdivision list response."""

    items: list[SubdivisionReadModel]
    total: int


# ------------------------------------------------------------------ #
#  Subdivision Type
# ------------------------------------------------------------------ #


class SubdivisionTypeTranslationReadModel(CamelModel):
    """Single translation row for a subdivision type."""

    lang_code: str
    name: str


class SubdivisionTypeReadModel(CamelModel):
    """Subdivision type with inline translations."""

    code: str
    sort_order: int
    translations: list[SubdivisionTypeTranslationReadModel] = Field(
        default_factory=list
    )


class SubdivisionTypeListReadModel(CamelModel):
    """Subdivision type list response."""

    items: list[SubdivisionTypeReadModel]
    total: int


# ------------------------------------------------------------------ #
#  Country-Currency link
# ------------------------------------------------------------------ #


class CountryCurrencyLinkReadModel(CamelModel):
    """A single country-currency association."""

    currency_code: str
    is_primary: bool


# ------------------------------------------------------------------ #
#  District
# ------------------------------------------------------------------ #


class DistrictTranslationReadModel(CamelModel):
    """Single translation row for a district."""

    lang_code: str
    name: str
    official_name: str | None = None
    local_variant: str | None = None


class DistrictReadModel(CamelModel):
    """District with inline translations."""

    id: str
    subdivision_code: str
    type_code: str
    oktmo_prefix: str | None = None
    fias_guid: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    is_active: bool = True
    sort_order: int = 0
    translations: list[DistrictTranslationReadModel] = Field(default_factory=list)


class DistrictListReadModel(CamelModel):
    """District list response."""

    items: list[DistrictReadModel]
    total: int


# ------------------------------------------------------------------ #
#  District Type
# ------------------------------------------------------------------ #


class DistrictTypeTranslationReadModel(CamelModel):
    """Single translation row for a district type."""

    lang_code: str
    name: str


class DistrictTypeReadModel(CamelModel):
    """District type with inline translations."""

    code: str
    sort_order: int
    translations: list[DistrictTypeTranslationReadModel] = Field(default_factory=list)


class DistrictTypeListReadModel(CamelModel):
    """District type list response."""

    items: list[DistrictTypeReadModel]
    total: int
