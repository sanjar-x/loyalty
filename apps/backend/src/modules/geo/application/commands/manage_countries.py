"""Admin command handlers for country CRUD and translations.

Reference-data management — uses AsyncSession directly (no UoW/aggregates).
"""

from dataclasses import dataclass

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.modules.geo.application.commands import safe_commit
from src.modules.geo.application.queries.read_models import (
    CountryCurrencyLinkReadModel,
    CountryReadModel,
    CountryTranslationReadModel,
)
from src.modules.geo.domain.exceptions import CountryNotFoundError
from src.modules.geo.infrastructure.models import (
    CountryCurrencyModel,
    CountryModel,
    CountryTranslationModel,
    CurrencyModel,
    LanguageModel,
)
from src.shared.exceptions import (
    ConflictError,
    UnprocessableEntityError,
    ValidationError,
)

logger = structlog.get_logger(__name__)


# ------------------------------------------------------------------ #
#  Create
# ------------------------------------------------------------------ #


@dataclass(frozen=True)
class CreateCountryCommand:
    alpha2: str
    alpha3: str
    numeric: str


class CreateCountryHandler:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def handle(self, command: CreateCountryCommand) -> CountryReadModel:
        existing = await self._session.get(CountryModel, command.alpha2)
        if existing:
            raise ConflictError(
                message=f"Country '{command.alpha2}' already exists.",
                error_code="COUNTRY_ALREADY_EXISTS",
                details={"alpha2": command.alpha2},
            )

        orm = CountryModel(
            alpha2=command.alpha2,
            alpha3=command.alpha3,
            numeric=command.numeric,
        )
        self._session.add(orm)
        await safe_commit(self._session)

        logger.info("country.created", alpha2=command.alpha2)
        return CountryReadModel(
            alpha2=orm.alpha2,
            alpha3=orm.alpha3,
            numeric=orm.numeric,
        )


# ------------------------------------------------------------------ #
#  Update
# ------------------------------------------------------------------ #


@dataclass(frozen=True)
class UpdateCountryCommand:
    alpha2: str
    alpha3: str | None = None
    numeric: str | None = None
    _provided_fields: frozenset[str] = frozenset()


class UpdateCountryHandler:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def handle(self, command: UpdateCountryCommand) -> CountryReadModel:
        orm = await self._session.get(CountryModel, command.alpha2)
        if orm is None:
            raise CountryNotFoundError(command.alpha2)

        for field in command._provided_fields:
            if field == "alpha2":
                continue
            value = getattr(command, field, None)
            if value is not None:
                setattr(orm, field, value)

        await safe_commit(self._session)
        await self._session.refresh(orm)

        logger.info("country.updated", alpha2=command.alpha2)
        return CountryReadModel(
            alpha2=orm.alpha2,
            alpha3=orm.alpha3,
            numeric=orm.numeric,
        )


# ------------------------------------------------------------------ #
#  Delete
# ------------------------------------------------------------------ #


class DeleteCountryHandler:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def handle(self, alpha2: str) -> None:
        orm = await self._session.get(CountryModel, alpha2)
        if orm is None:
            raise CountryNotFoundError(alpha2)

        await self._session.delete(orm)
        await safe_commit(self._session)
        logger.info("country.deleted", alpha2=alpha2)


# ------------------------------------------------------------------ #
#  Upsert Translations
# ------------------------------------------------------------------ #


@dataclass(frozen=True)
class CountryTranslationItem:
    lang_code: str
    name: str
    official_name: str | None = None


@dataclass(frozen=True)
class UpsertCountryTranslationsCommand:
    alpha2: str
    translations: list[CountryTranslationItem]


class UpsertCountryTranslationsHandler:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def handle(
        self, command: UpsertCountryTranslationsCommand
    ) -> list[CountryTranslationReadModel]:
        stmt = (
            select(CountryModel)
            .where(CountryModel.alpha2 == command.alpha2)
            .options(selectinload(CountryModel.translations))
        )
        result = await self._session.execute(stmt)
        country = result.scalar_one_or_none()
        if country is None:
            raise CountryNotFoundError(command.alpha2)

        # Validate all language codes exist
        for item in command.translations:
            if await self._session.get(LanguageModel, item.lang_code) is None:
                raise UnprocessableEntityError(
                    message=f"Language '{item.lang_code}' not found.",
                    error_code="LANGUAGE_NOT_FOUND",
                    details={"lang_code": item.lang_code},
                )

        existing = {tr.lang_code: tr for tr in country.translations}

        for item in command.translations:
            if item.lang_code in existing:
                existing[item.lang_code].name = item.name
                existing[item.lang_code].official_name = item.official_name
            else:
                country.translations.append(
                    CountryTranslationModel(
                        country_code=command.alpha2,
                        lang_code=item.lang_code,
                        name=item.name,
                        official_name=item.official_name,
                    )
                )

        await safe_commit(self._session)

        logger.info(
            "country.translations_upserted",
            alpha2=command.alpha2,
            count=len(command.translations),
        )
        return [
            CountryTranslationReadModel(
                lang_code=tr.lang_code,
                name=tr.name,
                official_name=tr.official_name,
            )
            for tr in country.translations
        ]


# ------------------------------------------------------------------ #
#  Set Country-Currency Links
# ------------------------------------------------------------------ #


@dataclass(frozen=True)
class CountryCurrencyLinkItem:
    currency_code: str
    is_primary: bool = False


@dataclass(frozen=True)
class SetCountryCurrenciesCommand:
    alpha2: str
    currencies: list[CountryCurrencyLinkItem]


class SetCountryCurrenciesHandler:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def handle(
        self, command: SetCountryCurrenciesCommand
    ) -> list[CountryCurrencyLinkReadModel]:
        country = await self._session.get(CountryModel, command.alpha2)
        if country is None:
            raise CountryNotFoundError(command.alpha2)

        # Validate no duplicate currency codes
        codes = [item.currency_code for item in command.currencies]
        if len(codes) != len(set(codes)):
            raise ValidationError(
                message="Duplicate currency codes in request.",
                error_code="DUPLICATE_CURRENCY_CODES",
            )

        # Validate at most one primary
        primary_count = sum(1 for item in command.currencies if item.is_primary)
        if primary_count > 1:
            raise ValidationError(
                message="At most one currency can be marked as primary.",
                error_code="MULTIPLE_PRIMARY_CURRENCIES",
            )

        # Validate all currency codes exist
        for item in command.currencies:
            currency = await self._session.get(CurrencyModel, item.currency_code)
            if currency is None:
                raise UnprocessableEntityError(
                    message=f"Currency '{item.currency_code}' not found.",
                    error_code="CURRENCY_NOT_FOUND",
                    details={"currency_code": item.currency_code},
                )

        # Delete existing links
        stmt = select(CountryCurrencyModel).where(
            CountryCurrencyModel.country_code == command.alpha2
        )
        result = await self._session.execute(stmt)
        for link in result.scalars().all():
            await self._session.delete(link)

        # Create new links
        new_links = []
        for item in command.currencies:
            link = CountryCurrencyModel(
                country_code=command.alpha2,
                currency_code=item.currency_code,
                is_primary=item.is_primary,
            )
            self._session.add(link)
            new_links.append(link)

        await safe_commit(self._session)

        logger.info(
            "country.currencies_set",
            alpha2=command.alpha2,
            count=len(command.currencies),
        )
        return [
            CountryCurrencyLinkReadModel(
                currency_code=link.currency_code,
                is_primary=link.is_primary,
            )
            for link in new_links
        ]
