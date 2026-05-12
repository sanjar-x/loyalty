"""Admin command handlers for subdivision & type CRUD and translations.

Reference-data management — uses AsyncSession directly (no UoW/aggregates).
"""

from dataclasses import dataclass
from decimal import Decimal

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.modules.geo.application.commands import safe_commit
from src.modules.geo.application.queries.read_models import (
    SubdivisionReadModel,
    SubdivisionTranslationReadModel,
    SubdivisionTypeListReadModel,
    SubdivisionTypeReadModel,
    SubdivisionTypeTranslationReadModel,
)
from src.modules.geo.domain.exceptions import (
    CountryNotFoundError,
    SubdivisionNotFoundError,
)
from src.modules.geo.infrastructure.models import (
    CountryModel,
    LanguageModel,
    SubdivisionModel,
    SubdivisionTranslationModel,
    SubdivisionTypeModel,
    SubdivisionTypeTranslationModel,
)
from src.shared.exceptions import ConflictError, NotFoundError, UnprocessableEntityError

logger = structlog.get_logger(__name__)


# ===================================================================
#  Subdivision CRUD
# ===================================================================


# ------------------------------------------------------------------ #
#  Create
# ------------------------------------------------------------------ #


@dataclass(frozen=True)
class CreateSubdivisionCommand:
    code: str
    country_code: str
    type_code: str
    parent_code: str | None = None
    latitude: Decimal | None = None
    longitude: Decimal | None = None
    sort_order: int = 0
    is_active: bool = True


class CreateSubdivisionHandler:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def handle(self, command: CreateSubdivisionCommand) -> SubdivisionReadModel:
        existing = await self._session.get(SubdivisionModel, command.code)
        if existing:
            raise ConflictError(
                message=f"Subdivision '{command.code}' already exists.",
                error_code="SUBDIVISION_ALREADY_EXISTS",
                details={"code": command.code},
            )

        # Validate FK references
        country = await self._session.get(CountryModel, command.country_code)
        if country is None:
            raise CountryNotFoundError(command.country_code)

        sub_type = await self._session.get(SubdivisionTypeModel, command.type_code)
        if sub_type is None:
            raise NotFoundError(
                message=f"Subdivision type '{command.type_code}' not found.",
                error_code="SUBDIVISION_TYPE_NOT_FOUND",
                details={"type_code": command.type_code},
            )

        if command.parent_code is not None:
            parent = await self._session.get(SubdivisionModel, command.parent_code)
            if parent is None:
                raise NotFoundError(
                    message=f"Parent subdivision '{command.parent_code}' not found.",
                    error_code="PARENT_SUBDIVISION_NOT_FOUND",
                    details={"parent_code": command.parent_code},
                )

        orm = SubdivisionModel(
            code=command.code,
            country_code=command.country_code,
            type_code=command.type_code,
            parent_code=command.parent_code,
            latitude=command.latitude,
            longitude=command.longitude,
            sort_order=command.sort_order,
            is_active=command.is_active,
        )
        self._session.add(orm)
        await safe_commit(self._session)

        logger.info("subdivision.created", code=command.code)
        return SubdivisionReadModel(
            code=orm.code,
            country_code=orm.country_code,
            type_code=orm.type_code,
            parent_code=orm.parent_code,
            latitude=float(orm.latitude) if orm.latitude is not None else None,
            longitude=float(orm.longitude) if orm.longitude is not None else None,
            is_active=orm.is_active,
            sort_order=orm.sort_order,
        )


# ------------------------------------------------------------------ #
#  Update
# ------------------------------------------------------------------ #


@dataclass(frozen=True)
class UpdateSubdivisionCommand:
    code: str
    type_code: str | None = None
    parent_code: str | None = None
    latitude: Decimal | None = None
    longitude: Decimal | None = None
    sort_order: int | None = None
    is_active: bool | None = None
    _provided_fields: frozenset[str] = frozenset()


class UpdateSubdivisionHandler:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def handle(self, command: UpdateSubdivisionCommand) -> SubdivisionReadModel:
        orm = await self._session.get(SubdivisionModel, command.code)
        if orm is None:
            raise SubdivisionNotFoundError(command.code)

        for field in command._provided_fields:
            if field in ("code", "country_code"):
                continue
            if hasattr(orm, field):
                setattr(orm, field, getattr(command, field))

        await safe_commit(self._session)
        await self._session.refresh(orm)

        logger.info("subdivision.updated", code=command.code)
        return SubdivisionReadModel(
            code=orm.code,
            country_code=orm.country_code,
            type_code=orm.type_code,
            parent_code=orm.parent_code,
            latitude=float(orm.latitude) if orm.latitude is not None else None,
            longitude=float(orm.longitude) if orm.longitude is not None else None,
            is_active=orm.is_active,
            sort_order=orm.sort_order,
        )


# ------------------------------------------------------------------ #
#  Delete
# ------------------------------------------------------------------ #


class DeleteSubdivisionHandler:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def handle(self, code: str) -> None:
        orm = await self._session.get(SubdivisionModel, code)
        if orm is None:
            raise SubdivisionNotFoundError(code)

        await self._session.delete(orm)
        await safe_commit(self._session)
        logger.info("subdivision.deleted", code=code)


# ------------------------------------------------------------------ #
#  Upsert Translations
# ------------------------------------------------------------------ #


@dataclass(frozen=True)
class SubdivisionTranslationItem:
    lang_code: str
    name: str
    official_name: str | None = None
    local_variant: str | None = None


@dataclass(frozen=True)
class UpsertSubdivisionTranslationsCommand:
    code: str
    translations: list[SubdivisionTranslationItem]


class UpsertSubdivisionTranslationsHandler:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def handle(
        self, command: UpsertSubdivisionTranslationsCommand
    ) -> list[SubdivisionTranslationReadModel]:
        stmt = (
            select(SubdivisionModel)
            .where(SubdivisionModel.code == command.code)
            .options(selectinload(SubdivisionModel.translations))
        )
        result = await self._session.execute(stmt)
        subdivision = result.scalar_one_or_none()
        if subdivision is None:
            raise SubdivisionNotFoundError(command.code)

        # Validate all language codes exist
        for item in command.translations:
            if await self._session.get(LanguageModel, item.lang_code) is None:
                raise UnprocessableEntityError(
                    message=f"Language '{item.lang_code}' not found.",
                    error_code="LANGUAGE_NOT_FOUND",
                    details={"lang_code": item.lang_code},
                )

        existing = {tr.lang_code: tr for tr in subdivision.translations}

        for item in command.translations:
            if item.lang_code in existing:
                existing[item.lang_code].name = item.name
                existing[item.lang_code].official_name = item.official_name
                existing[item.lang_code].local_variant = item.local_variant
            else:
                subdivision.translations.append(
                    SubdivisionTranslationModel(
                        subdivision_code=command.code,
                        lang_code=item.lang_code,
                        name=item.name,
                        official_name=item.official_name,
                        local_variant=item.local_variant,
                    )
                )

        await safe_commit(self._session)

        logger.info(
            "subdivision.translations_upserted",
            code=command.code,
            count=len(command.translations),
        )
        return [
            SubdivisionTranslationReadModel(
                lang_code=tr.lang_code,
                name=tr.name,
                official_name=tr.official_name,
                local_variant=tr.local_variant,
            )
            for tr in subdivision.translations
        ]


# ===================================================================
#  Subdivision Type CRUD
# ===================================================================


# ------------------------------------------------------------------ #
#  List
# ------------------------------------------------------------------ #


class ListSubdivisionTypesHandler:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def handle(
        self, offset: int = 0, limit: int = 50
    ) -> SubdivisionTypeListReadModel:
        count_stmt = select(func.count()).select_from(SubdivisionTypeModel)
        total = (await self._session.execute(count_stmt)).scalar_one()

        stmt = (
            select(SubdivisionTypeModel)
            .options(selectinload(SubdivisionTypeModel.translations))
            .order_by(SubdivisionTypeModel.sort_order)
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        categories = result.scalars().unique().all()

        items = [
            SubdivisionTypeReadModel(
                code=c.code,
                sort_order=c.sort_order,
                translations=[
                    SubdivisionTypeTranslationReadModel(
                        lang_code=tr.lang_code, name=tr.name
                    )
                    for tr in c.translations
                ],
            )
            for c in categories
        ]

        return SubdivisionTypeListReadModel(items=items, total=total)


# ------------------------------------------------------------------ #
#  Create
# ------------------------------------------------------------------ #


@dataclass(frozen=True)
class CreateSubdivisionTypeCommand:
    code: str
    sort_order: int = 0


class CreateSubdivisionTypeHandler:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def handle(
        self, command: CreateSubdivisionTypeCommand
    ) -> SubdivisionTypeReadModel:
        existing = await self._session.get(SubdivisionTypeModel, command.code)
        if existing:
            raise ConflictError(
                message=f"Subdivision type '{command.code}' already exists.",
                error_code="SUBDIVISION_TYPE_ALREADY_EXISTS",
                details={"code": command.code},
            )

        orm = SubdivisionTypeModel(
            code=command.code,
            sort_order=command.sort_order,
        )
        self._session.add(orm)
        await safe_commit(self._session)

        logger.info("subdivision_type.created", code=command.code)
        return SubdivisionTypeReadModel(code=orm.code, sort_order=orm.sort_order)


# ------------------------------------------------------------------ #
#  Update
# ------------------------------------------------------------------ #


@dataclass(frozen=True)
class UpdateSubdivisionTypeCommand:
    code: str
    sort_order: int | None = None
    _provided_fields: frozenset[str] = frozenset()


class UpdateSubdivisionTypeHandler:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def handle(
        self, command: UpdateSubdivisionTypeCommand
    ) -> SubdivisionTypeReadModel:
        orm = await self._session.get(SubdivisionTypeModel, command.code)
        if orm is None:
            raise NotFoundError(
                message=f"Subdivision type '{command.code}' not found.",
                error_code="SUBDIVISION_TYPE_NOT_FOUND",
                details={"code": command.code},
            )

        for field in command._provided_fields:
            if field == "code":
                continue
            if hasattr(orm, field):
                setattr(orm, field, getattr(command, field))

        await safe_commit(self._session)
        await self._session.refresh(orm)

        logger.info("subdivision_type.updated", code=command.code)
        return SubdivisionTypeReadModel(code=orm.code, sort_order=orm.sort_order)


# ------------------------------------------------------------------ #
#  Delete
# ------------------------------------------------------------------ #


class DeleteSubdivisionTypeHandler:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def handle(self, code: str) -> None:
        orm = await self._session.get(SubdivisionTypeModel, code)
        if orm is None:
            raise NotFoundError(
                message=f"Subdivision type '{code}' not found.",
                error_code="SUBDIVISION_TYPE_NOT_FOUND",
                details={"code": code},
            )

        await self._session.delete(orm)
        await safe_commit(self._session)
        logger.info("subdivision_type.deleted", code=code)


# ------------------------------------------------------------------ #
#  Upsert Category Translations
# ------------------------------------------------------------------ #


@dataclass(frozen=True)
class SubdivisionTypeTranslationItem:
    lang_code: str
    name: str


@dataclass(frozen=True)
class UpsertSubdivisionTypeTranslationsCommand:
    code: str
    translations: list[SubdivisionTypeTranslationItem]


class UpsertSubdivisionTypeTranslationsHandler:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def handle(
        self, command: UpsertSubdivisionTypeTranslationsCommand
    ) -> list[SubdivisionTypeTranslationReadModel]:
        stmt = (
            select(SubdivisionTypeModel)
            .where(SubdivisionTypeModel.code == command.code)
            .options(selectinload(SubdivisionTypeModel.translations))
        )
        result = await self._session.execute(stmt)
        sub_type = result.scalar_one_or_none()
        if sub_type is None:
            raise NotFoundError(
                message=f"Subdivision type '{command.code}' not found.",
                error_code="SUBDIVISION_TYPE_NOT_FOUND",
                details={"code": command.code},
            )

        # Validate all language codes exist
        for item in command.translations:
            if await self._session.get(LanguageModel, item.lang_code) is None:
                raise UnprocessableEntityError(
                    message=f"Language '{item.lang_code}' not found.",
                    error_code="LANGUAGE_NOT_FOUND",
                    details={"lang_code": item.lang_code},
                )

        existing = {tr.lang_code: tr for tr in sub_type.translations}

        for item in command.translations:
            if item.lang_code in existing:
                existing[item.lang_code].name = item.name
            else:
                sub_type.translations.append(
                    SubdivisionTypeTranslationModel(
                        type_code=command.code,
                        lang_code=item.lang_code,
                        name=item.name,
                    )
                )

        await safe_commit(self._session)

        logger.info(
            "subdivision_type.translations_upserted",
            code=command.code,
            count=len(command.translations),
        )
        return [
            SubdivisionTypeTranslationReadModel(lang_code=tr.lang_code, name=tr.name)
            for tr in sub_type.translations
        ]
