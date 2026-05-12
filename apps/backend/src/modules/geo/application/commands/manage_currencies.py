"""Admin command handlers for currency CRUD and translations.

Reference-data management — uses AsyncSession directly (no UoW/aggregates).
"""

from dataclasses import dataclass

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.modules.geo.application.commands import safe_commit
from src.modules.geo.application.queries.read_models import (
    CurrencyReadModel,
    CurrencyTranslationReadModel,
)
from src.modules.geo.domain.exceptions import CurrencyNotFoundError
from src.modules.geo.infrastructure.models import (
    CurrencyModel,
    CurrencyTranslationModel,
    LanguageModel,
)
from src.shared.exceptions import ConflictError, UnprocessableEntityError

logger = structlog.get_logger(__name__)


# ------------------------------------------------------------------ #
#  Create
# ------------------------------------------------------------------ #


@dataclass(frozen=True)
class CreateCurrencyCommand:
    code: str
    numeric: str
    name: str
    minor_unit: int | None = None
    is_active: bool = True
    sort_order: int = 0


class CreateCurrencyHandler:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def handle(self, command: CreateCurrencyCommand) -> CurrencyReadModel:
        existing = await self._session.get(CurrencyModel, command.code)
        if existing:
            raise ConflictError(
                message=f"Currency '{command.code}' already exists.",
                error_code="CURRENCY_ALREADY_EXISTS",
                details={"code": command.code},
            )

        orm = CurrencyModel(
            code=command.code,
            numeric=command.numeric,
            name=command.name,
            minor_unit=command.minor_unit,
            is_active=command.is_active,
            sort_order=command.sort_order,
        )
        self._session.add(orm)
        await safe_commit(self._session)

        logger.info("currency.created", code=command.code)
        return CurrencyReadModel(
            code=orm.code,
            numeric=orm.numeric,
            name=orm.name,
            minor_unit=orm.minor_unit,
            is_active=orm.is_active,
            sort_order=orm.sort_order,
        )


# ------------------------------------------------------------------ #
#  Update
# ------------------------------------------------------------------ #


@dataclass(frozen=True)
class UpdateCurrencyCommand:
    code: str
    numeric: str | None = None
    name: str | None = None
    minor_unit: int | None = None
    is_active: bool | None = None
    sort_order: int | None = None
    _provided_fields: frozenset[str] = frozenset()


class UpdateCurrencyHandler:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def handle(self, command: UpdateCurrencyCommand) -> CurrencyReadModel:
        orm = await self._session.get(CurrencyModel, command.code)
        if orm is None:
            raise CurrencyNotFoundError(command.code)

        for field in command._provided_fields:
            if field == "code":
                continue
            if hasattr(orm, field):
                setattr(orm, field, getattr(command, field))

        await safe_commit(self._session)
        await self._session.refresh(orm)

        logger.info("currency.updated", code=command.code)
        return CurrencyReadModel(
            code=orm.code,
            numeric=orm.numeric,
            name=orm.name,
            minor_unit=orm.minor_unit,
            is_active=orm.is_active,
            sort_order=orm.sort_order,
        )


# ------------------------------------------------------------------ #
#  Delete
# ------------------------------------------------------------------ #


class DeleteCurrencyHandler:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def handle(self, code: str) -> None:
        orm = await self._session.get(CurrencyModel, code)
        if orm is None:
            raise CurrencyNotFoundError(code)

        await self._session.delete(orm)
        await safe_commit(self._session)
        logger.info("currency.deleted", code=code)


# ------------------------------------------------------------------ #
#  Upsert Translations
# ------------------------------------------------------------------ #


@dataclass(frozen=True)
class CurrencyTranslationItem:
    lang_code: str
    name: str


@dataclass(frozen=True)
class UpsertCurrencyTranslationsCommand:
    code: str
    translations: list[CurrencyTranslationItem]


class UpsertCurrencyTranslationsHandler:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def handle(
        self, command: UpsertCurrencyTranslationsCommand
    ) -> list[CurrencyTranslationReadModel]:
        stmt = (
            select(CurrencyModel)
            .where(CurrencyModel.code == command.code)
            .options(selectinload(CurrencyModel.translations))
        )
        result = await self._session.execute(stmt)
        currency = result.scalar_one_or_none()
        if currency is None:
            raise CurrencyNotFoundError(command.code)

        # Validate all language codes exist
        for item in command.translations:
            if await self._session.get(LanguageModel, item.lang_code) is None:
                raise UnprocessableEntityError(
                    message=f"Language '{item.lang_code}' not found.",
                    error_code="LANGUAGE_NOT_FOUND",
                    details={"lang_code": item.lang_code},
                )

        existing = {tr.lang_code: tr for tr in currency.translations}

        for item in command.translations:
            if item.lang_code in existing:
                existing[item.lang_code].name = item.name
            else:
                currency.translations.append(
                    CurrencyTranslationModel(
                        currency_code=command.code,
                        lang_code=item.lang_code,
                        name=item.name,
                    )
                )

        await safe_commit(self._session)

        logger.info(
            "currency.translations_upserted",
            code=command.code,
            count=len(command.translations),
        )
        return [
            CurrencyTranslationReadModel(lang_code=tr.lang_code, name=tr.name)
            for tr in currency.translations
        ]
