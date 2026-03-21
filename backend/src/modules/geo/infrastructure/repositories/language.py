"""Language repository — Data Mapper implementation.

Translates between the ``languages`` ORM table and the domain
:class:`~src.modules.geo.domain.value_objects.Language` value object.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.geo.domain.interfaces import ILanguageRepository
from src.modules.geo.domain.value_objects import Language
from src.modules.geo.infrastructure.models import LanguageModel


class LanguageRepository(ILanguageRepository):
    """SQLAlchemy read-only repository for languages."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @staticmethod
    def _to_domain(orm: LanguageModel) -> Language:
        return Language(
            code=orm.code,
            iso639_1=orm.iso639_1,
            iso639_2=orm.iso639_2,
            iso639_3=orm.iso639_3,
            script=orm.script,
            name_en=orm.name_en,
            name_native=orm.name_native,
            direction=orm.direction,
        )

    async def get_by_code(self, code: str) -> Language | None:
        orm = await self._session.get(LanguageModel, code)
        return self._to_domain(orm) if orm else None

    async def list_active(self) -> list[Language]:
        stmt = (
            select(LanguageModel)
            .where(LanguageModel.is_active.is_(True))
            .order_by(LanguageModel.sort_order)
        )
        result = await self._session.execute(stmt)
        return [self._to_domain(orm) for orm in result.scalars().all()]

    async def list_all(self) -> list[Language]:
        stmt = select(LanguageModel).order_by(LanguageModel.sort_order)
        result = await self._session.execute(stmt)
        return [self._to_domain(orm) for orm in result.scalars().all()]

    async def get_default(self) -> Language | None:
        stmt = select(LanguageModel).where(LanguageModel.is_default.is_(True)).limit(1)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None
