"""Pydantic request schemas for Geo admin CRUD endpoints.

All schemas inherit ``CamelModel`` for automatic snake_case → camelCase
JSON aliasing.
"""

from decimal import Decimal

from pydantic import Field, model_validator

from src.shared.schemas import CamelModel

# ------------------------------------------------------------------ #
#  Country
# ------------------------------------------------------------------ #


class CreateCountryRequest(CamelModel):
    alpha2: str = Field(..., min_length=2, max_length=2, pattern=r"^[A-Z]{2}$")
    alpha3: str = Field(..., min_length=3, max_length=3, pattern=r"^[A-Z]{3}$")
    numeric: str = Field(..., min_length=3, max_length=3, pattern=r"^\d{3}$")


class UpdateCountryRequest(CamelModel):
    alpha3: str | None = Field(None, min_length=3, max_length=3, pattern=r"^[A-Z]{3}$")
    numeric: str | None = Field(None, min_length=3, max_length=3, pattern=r"^\d{3}$")

    @model_validator(mode="after")
    def at_least_one_field(self) -> UpdateCountryRequest:
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        return self


class CountryTranslationInput(CamelModel):
    lang_code: str = Field(..., min_length=2, max_length=12)
    name: str = Field(..., min_length=1, max_length=255)
    official_name: str | None = Field(None, max_length=255)


class UpsertCountryTranslationsRequest(CamelModel):
    translations: list[CountryTranslationInput] = Field(..., min_length=1)


# ------------------------------------------------------------------ #
#  Currency
# ------------------------------------------------------------------ #


class CreateCurrencyRequest(CamelModel):
    code: str = Field(..., min_length=3, max_length=3, pattern=r"^[A-Z]{3}$")
    numeric: str = Field(..., min_length=3, max_length=3, pattern=r"^\d{3}$")
    name: str = Field(..., min_length=1, max_length=100)
    minor_unit: int | None = Field(None, ge=0, le=4)
    is_active: bool = True
    sort_order: int = Field(0, ge=0)


class UpdateCurrencyRequest(CamelModel):
    numeric: str | None = Field(None, min_length=3, max_length=3, pattern=r"^\d{3}$")
    name: str | None = Field(None, min_length=1, max_length=100)
    minor_unit: int | None = None
    is_active: bool | None = None
    sort_order: int | None = Field(None, ge=0)

    @model_validator(mode="after")
    def at_least_one_field(self) -> UpdateCurrencyRequest:
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        return self


class CurrencyTranslationInput(CamelModel):
    lang_code: str = Field(..., min_length=2, max_length=12)
    name: str = Field(..., min_length=1, max_length=100)


class UpsertCurrencyTranslationsRequest(CamelModel):
    translations: list[CurrencyTranslationInput] = Field(..., min_length=1)


class CountryCurrencyLinkInput(CamelModel):
    currency_code: str = Field(..., min_length=3, max_length=3, pattern=r"^[A-Z]{3}$")
    is_primary: bool = False


class SetCountryCurrenciesRequest(CamelModel):
    currencies: list[CountryCurrencyLinkInput] = Field(..., min_length=0)


# ------------------------------------------------------------------ #
#  Language
# ------------------------------------------------------------------ #


class CreateLanguageRequest(CamelModel):
    code: str = Field(..., min_length=2, max_length=12)
    iso639_1: str | None = Field(None, min_length=2, max_length=2)
    iso639_2: str | None = Field(None, min_length=3, max_length=3)
    iso639_3: str | None = Field(None, min_length=3, max_length=3)
    script: str | None = Field(None, min_length=4, max_length=4)
    name_en: str = Field(..., min_length=1, max_length=100)
    name_native: str = Field(..., min_length=1, max_length=100)
    direction: str = Field("ltr", pattern=r"^(ltr|rtl)$")
    is_active: bool = True
    is_default: bool = False
    sort_order: int = Field(0, ge=0)


class UpdateLanguageRequest(CamelModel):
    iso639_1: str | None = None
    iso639_2: str | None = None
    iso639_3: str | None = None
    script: str | None = None
    name_en: str | None = Field(None, min_length=1, max_length=100)
    name_native: str | None = Field(None, min_length=1, max_length=100)
    direction: str | None = Field(None, pattern=r"^(ltr|rtl)$")
    is_active: bool | None = None
    is_default: bool | None = None
    sort_order: int | None = Field(None, ge=0)

    @model_validator(mode="after")
    def at_least_one_field(self) -> UpdateLanguageRequest:
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        return self


# ------------------------------------------------------------------ #
#  Subdivision
# ------------------------------------------------------------------ #


class CreateSubdivisionRequest(CamelModel):
    code: str = Field(
        ..., min_length=4, max_length=10, pattern=r"^[A-Z]{2}-[A-Z0-9]{1,8}$"
    )
    country_code: str = Field(..., min_length=2, max_length=2, pattern=r"^[A-Z]{2}$")
    category_code: str = Field(..., min_length=1, max_length=60)
    parent_code: str | None = Field(None, max_length=10)
    latitude: Decimal | None = None
    longitude: Decimal | None = None
    sort_order: int = Field(0, ge=0)
    is_active: bool = True


class UpdateSubdivisionRequest(CamelModel):
    category_code: str | None = Field(None, min_length=1, max_length=60)
    parent_code: str | None = None
    latitude: Decimal | None = None
    longitude: Decimal | None = None
    sort_order: int | None = Field(None, ge=0)
    is_active: bool | None = None

    @model_validator(mode="after")
    def at_least_one_field(self) -> UpdateSubdivisionRequest:
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        return self


class SubdivisionTranslationInput(CamelModel):
    lang_code: str = Field(..., min_length=2, max_length=12)
    name: str = Field(..., min_length=1, max_length=255)
    official_name: str | None = Field(None, max_length=255)
    local_variant: str | None = Field(None, max_length=255)


class UpsertSubdivisionTranslationsRequest(CamelModel):
    translations: list[SubdivisionTranslationInput] = Field(..., min_length=1)


# ------------------------------------------------------------------ #
#  Subdivision Category
# ------------------------------------------------------------------ #


class CreateSubdivisionCategoryRequest(CamelModel):
    code: str = Field(..., min_length=1, max_length=60)
    sort_order: int = Field(0, ge=0)


class UpdateSubdivisionCategoryRequest(CamelModel):
    sort_order: int | None = Field(None, ge=0)

    @model_validator(mode="after")
    def at_least_one_field(self) -> UpdateSubdivisionCategoryRequest:
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        return self


class SubdivisionCategoryTranslationInput(CamelModel):
    lang_code: str = Field(..., min_length=2, max_length=12)
    name: str = Field(..., min_length=1, max_length=100)


class UpsertSubdivisionCategoryTranslationsRequest(CamelModel):
    translations: list[SubdivisionCategoryTranslationInput] = Field(..., min_length=1)
