"""Admin command handlers for language CRUD.

Reference-data management — uses AsyncSession directly (no UoW/aggregates).
"""

from dataclasses import dataclass

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.geo.application.commands import safe_commit
from src.modules.geo.application.queries.read_models import LanguageReadModel
from src.modules.geo.domain.exceptions import LanguageNotFoundError
from src.modules.geo.infrastructure.models import LanguageModel
from src.shared.exceptions import ConflictError

logger = structlog.get_logger(__name__)


# ------------------------------------------------------------------ #
#  Create
# ------------------------------------------------------------------ #


@dataclass(frozen=True)
class CreateLanguageCommand:
    code: str
    iso639_1: str | None = None
    iso639_2: str | None = None
    iso639_3: str | None = None
    script: str | None = None
    name_en: str = ""
    name_native: str = ""
    direction: str = "ltr"
    is_active: bool = True
    is_default: bool = False
    sort_order: int = 0


class CreateLanguageHandler:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def handle(self, command: CreateLanguageCommand) -> LanguageReadModel:
        existing = await self._session.get(LanguageModel, command.code)
        if existing:
            raise ConflictError(
                message=f"Language '{command.code}' already exists.",
                error_code="LANGUAGE_ALREADY_EXISTS",
                details={"code": command.code},
            )

        orm = LanguageModel(
            code=command.code,
            iso639_1=command.iso639_1,
            iso639_2=command.iso639_2,
            iso639_3=command.iso639_3,
            script=command.script,
            name_en=command.name_en,
            name_native=command.name_native,
            direction=command.direction,
            is_active=command.is_active,
            is_default=command.is_default,
            sort_order=command.sort_order,
        )
        self._session.add(orm)
        await safe_commit(self._session)

        logger.info("language.created", code=command.code)
        return self._to_read_model(orm)

    @staticmethod
    def _to_read_model(orm: LanguageModel) -> LanguageReadModel:
        return LanguageReadModel(
            code=orm.code,
            iso639_1=orm.iso639_1,
            iso639_2=orm.iso639_2,
            iso639_3=orm.iso639_3,
            script=orm.script,
            name_en=orm.name_en,
            name_native=orm.name_native,
            direction=orm.direction,
            is_active=orm.is_active,
            is_default=orm.is_default,
            sort_order=orm.sort_order,
        )


# ------------------------------------------------------------------ #
#  Update
# ------------------------------------------------------------------ #


@dataclass(frozen=True)
class UpdateLanguageCommand:
    code: str
    iso639_1: str | None = None
    iso639_2: str | None = None
    iso639_3: str | None = None
    script: str | None = None
    name_en: str | None = None
    name_native: str | None = None
    direction: str | None = None
    is_active: bool | None = None
    is_default: bool | None = None
    sort_order: int | None = None
    _provided_fields: frozenset[str] = frozenset()


class UpdateLanguageHandler:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def handle(self, command: UpdateLanguageCommand) -> LanguageReadModel:
        orm = await self._session.get(LanguageModel, command.code)
        if orm is None:
            raise LanguageNotFoundError(command.code)

        for field in command._provided_fields:
            if field == "code":
                continue
            if hasattr(orm, field):
                setattr(orm, field, getattr(command, field))

        await safe_commit(self._session)
        await self._session.refresh(orm)

        logger.info("language.updated", code=command.code)
        return LanguageReadModel(
            code=orm.code,
            iso639_1=orm.iso639_1,
            iso639_2=orm.iso639_2,
            iso639_3=orm.iso639_3,
            script=orm.script,
            name_en=orm.name_en,
            name_native=orm.name_native,
            direction=orm.direction,
            is_active=orm.is_active,
            is_default=orm.is_default,
            sort_order=orm.sort_order,
        )


# ------------------------------------------------------------------ #
#  Delete
# ------------------------------------------------------------------ #


class DeleteLanguageHandler:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def handle(self, code: str) -> None:
        orm = await self._session.get(LanguageModel, code)
        if orm is None:
            raise LanguageNotFoundError(code)

        await self._session.delete(orm)
        await safe_commit(self._session)
        logger.info("language.deleted", code=code)
