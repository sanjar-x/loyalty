"""Read models (DTOs) for Geo query handlers.

Flat projections for the CQRS read side.  Carry no business logic —
only data for API responses.
"""

from pydantic import BaseModel, Field

# ------------------------------------------------------------------ #
#  Country
# ------------------------------------------------------------------ #


class CountryTranslationReadModel(BaseModel):
    """Single translation row for a country."""

    lang_code: str
    name: str
    official_name: str | None = None


class CountryReadModel(BaseModel):
    """Country with inline translations."""

    alpha2: str
    alpha3: str
    numeric: str
    translations: list[CountryTranslationReadModel] = Field(default_factory=list)


class CountryListReadModel(BaseModel):
    """Full country list response."""

    items: list[CountryReadModel]
    total: int


# ------------------------------------------------------------------ #
#  Currency
# ------------------------------------------------------------------ #


class CurrencyTranslationReadModel(BaseModel):
    """Single translation row for a currency."""

    lang_code: str
    name: str


class CurrencyReadModel(BaseModel):
    """Currency with inline translations."""

    code: str
    numeric: str
    name: str
    minor_unit: int | None = None
    is_active: bool = True
    sort_order: int = 0
    translations: list[CurrencyTranslationReadModel] = Field(default_factory=list)


class CurrencyListReadModel(BaseModel):
    """Currency list response."""

    items: list[CurrencyReadModel]
    total: int


# ------------------------------------------------------------------ #
#  Language
# ------------------------------------------------------------------ #


class LanguageReadModel(BaseModel):
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


class LanguageListReadModel(BaseModel):
    """Language list response."""

    items: list[LanguageReadModel]
    total: int


# ------------------------------------------------------------------ #
#  Subdivision
# ------------------------------------------------------------------ #


class SubdivisionTranslationReadModel(BaseModel):
    """Single translation row for a subdivision."""

    lang_code: str
    name: str
    official_name: str | None = None
    local_variant: str | None = None


class SubdivisionReadModel(BaseModel):
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


class SubdivisionListReadModel(BaseModel):
    """Subdivision list response."""

    items: list[SubdivisionReadModel]
    total: int


# ------------------------------------------------------------------ #
#  Subdivision Type
# ------------------------------------------------------------------ #


class SubdivisionTypeTranslationReadModel(BaseModel):
    """Single translation row for a subdivision type."""

    lang_code: str
    name: str


class SubdivisionTypeReadModel(BaseModel):
    """Subdivision type with inline translations."""

    code: str
    sort_order: int
    translations: list[SubdivisionTypeTranslationReadModel] = Field(
        default_factory=list
    )


class SubdivisionTypeListReadModel(BaseModel):
    """Subdivision type list response."""

    items: list[SubdivisionTypeReadModel]
    total: int


# ------------------------------------------------------------------ #
#  Country-Currency link
# ------------------------------------------------------------------ #


class CountryCurrencyLinkReadModel(BaseModel):
    """A single country-currency association."""

    currency_code: str
    is_primary: bool


# ------------------------------------------------------------------ #
#  District
# ------------------------------------------------------------------ #


class DistrictTranslationReadModel(BaseModel):
    """Single translation row for a district."""

    lang_code: str
    name: str
    official_name: str | None = None
    local_variant: str | None = None


class DistrictReadModel(BaseModel):
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


class DistrictListReadModel(BaseModel):
    """District list response."""

    items: list[DistrictReadModel]
    total: int


# ------------------------------------------------------------------ #
#  District Type
# ------------------------------------------------------------------ #


class DistrictTypeTranslationReadModel(BaseModel):
    """Single translation row for a district type."""

    lang_code: str
    name: str


class DistrictTypeReadModel(BaseModel):
    """District type with inline translations."""

    code: str
    sort_order: int
    translations: list[DistrictTypeTranslationReadModel] = Field(default_factory=list)


class DistrictTypeListReadModel(BaseModel):
    """District type list response."""

    items: list[DistrictTypeReadModel]
    total: int
