"""Admin command handlers for district & type CRUD and translations.

Reference-data management — uses AsyncSession directly (no UoW/aggregates).
"""

import uuid as uuid_mod
from dataclasses import dataclass
from decimal import Decimal

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.modules.geo.application.commands import safe_commit
from src.modules.geo.application.queries.read_models import (
    DistrictReadModel,
    DistrictTranslationReadModel,
    DistrictTypeListReadModel,
    DistrictTypeReadModel,
    DistrictTypeTranslationReadModel,
)
from src.modules.geo.domain.exceptions import (
    DistrictNotFoundError,
    SubdivisionNotFoundError,
)
from src.modules.geo.infrastructure.models import (
    DistrictModel,
    DistrictTranslationModel,
    DistrictTypeModel,
    DistrictTypeTranslationModel,
    LanguageModel,
    SubdivisionModel,
)
from src.shared.exceptions import ConflictError, NotFoundError, UnprocessableEntityError

logger = structlog.get_logger(__name__)


# ===================================================================
#  District CRUD
# ===================================================================


# ------------------------------------------------------------------ #
#  Create
# ------------------------------------------------------------------ #


@dataclass(frozen=True)
class CreateDistrictCommand:
    subdivision_code: str
    type_code: str
    oktmo_prefix: str | None = None
    fias_guid: str | None = None
    latitude: Decimal | None = None
    longitude: Decimal | None = None
    sort_order: int = 0
    is_active: bool = True


class CreateDistrictHandler:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def handle(self, command: CreateDistrictCommand) -> DistrictReadModel:
        # Validate FK references
        subdivision = await self._session.get(
            SubdivisionModel, command.subdivision_code
        )
        if subdivision is None:
            raise SubdivisionNotFoundError(command.subdivision_code)

        district_type = await self._session.get(DistrictTypeModel, command.type_code)
        if district_type is None:
            raise NotFoundError(
                message=f"District type '{command.type_code}' not found.",
                error_code="DISTRICT_TYPE_NOT_FOUND",
                details={"type_code": command.type_code},
            )

        # Validate oktmo_prefix/fias_guid only for RU subdivisions
        country_code = subdivision.country_code
        if command.oktmo_prefix is not None and country_code != "RU":
            raise UnprocessableEntityError(
                message="oktmo_prefix is only valid for Russian (RU) subdivisions.",
                error_code="OKTMO_NON_RUSSIAN",
                details={"country_code": country_code},
            )
        if command.fias_guid is not None and country_code != "RU":
            raise UnprocessableEntityError(
                message="fias_guid is only valid for Russian (RU) subdivisions.",
                error_code="FIAS_NON_RUSSIAN",
                details={"country_code": country_code},
            )

        fias_uuid = None
        if command.fias_guid is not None:
            try:
                fias_uuid = uuid_mod.UUID(command.fias_guid)
            except ValueError:
                raise UnprocessableEntityError(
                    message=f"Invalid UUID format for fias_guid: {command.fias_guid}",
                    error_code="INVALID_FIAS_GUID",
                    details={"fias_guid": command.fias_guid},
                ) from None

        orm = DistrictModel(
            subdivision_code=command.subdivision_code,
            type_code=command.type_code,
            oktmo_prefix=command.oktmo_prefix,
            fias_guid=fias_uuid,
            latitude=command.latitude,
            longitude=command.longitude,
            sort_order=command.sort_order,
            is_active=command.is_active,
        )
        self._session.add(orm)
        await safe_commit(self._session)

        logger.info(
            "district.created",
            district_id=str(orm.id),
            subdivision_code=command.subdivision_code,
        )
        return DistrictReadModel(
            id=str(orm.id),
            subdivision_code=orm.subdivision_code,
            type_code=orm.type_code,
            oktmo_prefix=orm.oktmo_prefix,
            fias_guid=str(orm.fias_guid) if orm.fias_guid is not None else None,
            latitude=float(orm.latitude) if orm.latitude is not None else None,
            longitude=float(orm.longitude) if orm.longitude is not None else None,
            is_active=orm.is_active,
            sort_order=orm.sort_order,
        )


# ------------------------------------------------------------------ #
#  Update
# ------------------------------------------------------------------ #


@dataclass(frozen=True)
class UpdateDistrictCommand:
    district_id: str
    type_code: str | None = None
    oktmo_prefix: str | None = None
    fias_guid: str | None = None
    latitude: Decimal | None = None
    longitude: Decimal | None = None
    sort_order: int | None = None
    is_active: bool | None = None
    _provided_fields: frozenset[str] = frozenset()


class UpdateDistrictHandler:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def handle(self, command: UpdateDistrictCommand) -> DistrictReadModel:
        try:
            parsed_id = uuid_mod.UUID(command.district_id)
        except ValueError:
            raise DistrictNotFoundError(command.district_id) from None

        orm = await self._session.get(DistrictModel, parsed_id)
        if orm is None:
            raise DistrictNotFoundError(command.district_id)

        provided = command._provided_fields

        # Validate type_code FK if being updated
        if "type_code" in provided and command.type_code is not None:
            district_type = await self._session.get(
                DistrictTypeModel, command.type_code
            )
            if district_type is None:
                raise NotFoundError(
                    message=f"District type '{command.type_code}' not found.",
                    error_code="DISTRICT_TYPE_NOT_FOUND",
                    details={"type_code": command.type_code},
                )

        # Validate oktmo_prefix/fias_guid only allowed for RU subdivisions
        subdivision = await self._session.get(SubdivisionModel, orm.subdivision_code)
        if subdivision is None:
            raise NotFoundError(
                message=f"Subdivision '{orm.subdivision_code}' not found.",
                error_code="SUBDIVISION_NOT_FOUND",
                details={"subdivision_code": orm.subdivision_code},
            )
        country_code = subdivision.country_code
        if (
            "oktmo_prefix" in provided
            and command.oktmo_prefix is not None
            and country_code != "RU"
        ):
            raise UnprocessableEntityError(
                message="oktmo_prefix is only valid for Russian (RU) subdivisions.",
                error_code="OKTMO_NON_RUSSIAN",
                details={"country_code": country_code},
            )
        if (
            "fias_guid" in provided
            and command.fias_guid is not None
            and country_code != "RU"
        ):
            raise UnprocessableEntityError(
                message="fias_guid is only valid for Russian (RU) subdivisions.",
                error_code="FIAS_NON_RUSSIAN",
                details={"country_code": country_code},
            )

        for field in provided:
            if field in ("district_id",):
                continue
            if field == "fias_guid" and command.fias_guid is not None:
                try:
                    setattr(orm, field, uuid_mod.UUID(command.fias_guid))
                except ValueError:
                    raise UnprocessableEntityError(
                        message=f"Invalid UUID format for fias_guid: {command.fias_guid}",
                        error_code="INVALID_FIAS_GUID",
                        details={"fias_guid": command.fias_guid},
                    ) from None
            elif hasattr(orm, field):
                setattr(orm, field, getattr(command, field))

        await safe_commit(self._session)
        await self._session.refresh(orm)

        logger.info("district.updated", district_id=command.district_id)
        return DistrictReadModel(
            id=str(orm.id),
            subdivision_code=orm.subdivision_code,
            type_code=orm.type_code,
            oktmo_prefix=orm.oktmo_prefix,
            fias_guid=str(orm.fias_guid) if orm.fias_guid is not None else None,
            latitude=float(orm.latitude) if orm.latitude is not None else None,
            longitude=float(orm.longitude) if orm.longitude is not None else None,
            is_active=orm.is_active,
            sort_order=orm.sort_order,
        )


# ------------------------------------------------------------------ #
#  Delete
# ------------------------------------------------------------------ #


class DeleteDistrictHandler:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def handle(self, district_id: str) -> None:
        try:
            parsed_id = uuid_mod.UUID(district_id)
        except ValueError:
            raise DistrictNotFoundError(district_id) from None

        orm = await self._session.get(DistrictModel, parsed_id)
        if orm is None:
            raise DistrictNotFoundError(district_id)

        await self._session.delete(orm)
        await safe_commit(self._session)
        logger.info("district.deleted", district_id=district_id)


# ------------------------------------------------------------------ #
#  Upsert Translations
# ------------------------------------------------------------------ #


@dataclass(frozen=True)
class DistrictTranslationItem:
    lang_code: str
    name: str
    official_name: str | None = None
    local_variant: str | None = None


@dataclass(frozen=True)
class UpsertDistrictTranslationsCommand:
    district_id: str
    translations: list[DistrictTranslationItem]


class UpsertDistrictTranslationsHandler:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def handle(
        self, command: UpsertDistrictTranslationsCommand
    ) -> list[DistrictTranslationReadModel]:
        try:
            parsed_id = uuid_mod.UUID(command.district_id)
        except ValueError:
            raise DistrictNotFoundError(command.district_id) from None

        stmt = (
            select(DistrictModel)
            .where(DistrictModel.id == parsed_id)
            .options(selectinload(DistrictModel.translations))
        )
        result = await self._session.execute(stmt)
        district = result.scalar_one_or_none()
        if district is None:
            raise DistrictNotFoundError(command.district_id)

        # Validate all language codes exist
        for item in command.translations:
            if await self._session.get(LanguageModel, item.lang_code) is None:
                raise UnprocessableEntityError(
                    message=f"Language '{item.lang_code}' not found.",
                    error_code="LANGUAGE_NOT_FOUND",
                    details={"lang_code": item.lang_code},
                )

        existing = {tr.lang_code: tr for tr in district.translations}

        for item in command.translations:
            if item.lang_code in existing:
                existing[item.lang_code].name = item.name
                existing[item.lang_code].official_name = item.official_name
                existing[item.lang_code].local_variant = item.local_variant
            else:
                district.translations.append(
                    DistrictTranslationModel(
                        district_id=parsed_id,
                        lang_code=item.lang_code,
                        name=item.name,
                        official_name=item.official_name,
                        local_variant=item.local_variant,
                    )
                )

        await safe_commit(self._session)

        logger.info(
            "district.translations_upserted",
            district_id=command.district_id,
            count=len(command.translations),
        )
        return [
            DistrictTranslationReadModel(
                lang_code=tr.lang_code,
                name=tr.name,
                official_name=tr.official_name,
                local_variant=tr.local_variant,
            )
            for tr in district.translations
        ]


# ===================================================================
#  District Type CRUD
# ===================================================================


# ------------------------------------------------------------------ #
#  List
# ------------------------------------------------------------------ #


class ListDistrictTypesHandler:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def handle(
        self, offset: int = 0, limit: int = 50
    ) -> DistrictTypeListReadModel:
        count_stmt = select(func.count()).select_from(DistrictTypeModel)
        total = (await self._session.execute(count_stmt)).scalar_one()

        stmt = (
            select(DistrictTypeModel)
            .options(selectinload(DistrictTypeModel.translations))
            .order_by(DistrictTypeModel.sort_order)
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        types = result.scalars().unique().all()

        items = [
            DistrictTypeReadModel(
                code=t.code,
                sort_order=t.sort_order,
                translations=[
                    DistrictTypeTranslationReadModel(
                        lang_code=tr.lang_code, name=tr.name
                    )
                    for tr in t.translations
                ],
            )
            for t in types
        ]

        return DistrictTypeListReadModel(items=items, total=total)


# ------------------------------------------------------------------ #
#  Create
# ------------------------------------------------------------------ #


@dataclass(frozen=True)
class CreateDistrictTypeCommand:
    code: str
    sort_order: int = 0


class CreateDistrictTypeHandler:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def handle(self, command: CreateDistrictTypeCommand) -> DistrictTypeReadModel:
        existing = await self._session.get(DistrictTypeModel, command.code)
        if existing:
            raise ConflictError(
                message=f"District type '{command.code}' already exists.",
                error_code="DISTRICT_TYPE_ALREADY_EXISTS",
                details={"code": command.code},
            )

        orm = DistrictTypeModel(
            code=command.code,
            sort_order=command.sort_order,
        )
        self._session.add(orm)
        await safe_commit(self._session)

        logger.info("district_type.created", code=command.code)
        return DistrictTypeReadModel(code=orm.code, sort_order=orm.sort_order)


# ------------------------------------------------------------------ #
#  Update
# ------------------------------------------------------------------ #


@dataclass(frozen=True)
class UpdateDistrictTypeCommand:
    code: str
    sort_order: int | None = None
    _provided_fields: frozenset[str] = frozenset()


class UpdateDistrictTypeHandler:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def handle(self, command: UpdateDistrictTypeCommand) -> DistrictTypeReadModel:
        orm = await self._session.get(DistrictTypeModel, command.code)
        if orm is None:
            raise NotFoundError(
                message=f"District type '{command.code}' not found.",
                error_code="DISTRICT_TYPE_NOT_FOUND",
                details={"code": command.code},
            )

        for field in command._provided_fields:
            if field == "code":
                continue
            if hasattr(orm, field):
                setattr(orm, field, getattr(command, field))

        await safe_commit(self._session)
        await self._session.refresh(orm)

        logger.info("district_type.updated", code=command.code)
        return DistrictTypeReadModel(code=orm.code, sort_order=orm.sort_order)


# ------------------------------------------------------------------ #
#  Delete
# ------------------------------------------------------------------ #


class DeleteDistrictTypeHandler:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def handle(self, code: str) -> None:
        orm = await self._session.get(DistrictTypeModel, code)
        if orm is None:
            raise NotFoundError(
                message=f"District type '{code}' not found.",
                error_code="DISTRICT_TYPE_NOT_FOUND",
                details={"code": code},
            )

        await self._session.delete(orm)
        await safe_commit(self._session)
        logger.info("district_type.deleted", code=code)


# ------------------------------------------------------------------ #
#  Upsert Type Translations
# ------------------------------------------------------------------ #


@dataclass(frozen=True)
class DistrictTypeTranslationItem:
    lang_code: str
    name: str


@dataclass(frozen=True)
class UpsertDistrictTypeTranslationsCommand:
    code: str
    translations: list[DistrictTypeTranslationItem]


class UpsertDistrictTypeTranslationsHandler:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def handle(
        self, command: UpsertDistrictTypeTranslationsCommand
    ) -> list[DistrictTypeTranslationReadModel]:
        stmt = (
            select(DistrictTypeModel)
            .where(DistrictTypeModel.code == command.code)
            .options(selectinload(DistrictTypeModel.translations))
        )
        result = await self._session.execute(stmt)
        district_type = result.scalar_one_or_none()
        if district_type is None:
            raise NotFoundError(
                message=f"District type '{command.code}' not found.",
                error_code="DISTRICT_TYPE_NOT_FOUND",
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

        existing = {tr.lang_code: tr for tr in district_type.translations}

        for item in command.translations:
            if item.lang_code in existing:
                existing[item.lang_code].name = item.name
            else:
                district_type.translations.append(
                    DistrictTypeTranslationModel(
                        type_code=command.code,
                        lang_code=item.lang_code,
                        name=item.name,
                    )
                )

        await safe_commit(self._session)

        logger.info(
            "district_type.translations_upserted",
            code=command.code,
            count=len(command.translations),
        )
        return [
            DistrictTypeTranslationReadModel(lang_code=tr.lang_code, name=tr.name)
            for tr in district_type.translations
        ]
