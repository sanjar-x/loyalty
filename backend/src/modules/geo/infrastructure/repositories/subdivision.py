"""Subdivision repository — Data Mapper implementation.

Translates between the ``subdivisions`` ORM table and the domain
:class:`~src.modules.geo.domain.value_objects.Subdivision` value object.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.geo.domain.interfaces import ISubdivisionRepository
from src.modules.geo.domain.value_objects import Subdivision
from src.modules.geo.infrastructure.models import SubdivisionModel


class SubdivisionRepository(ISubdivisionRepository):
    """SQLAlchemy read-only repository for subdivisions."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @staticmethod
    def _to_domain(orm: SubdivisionModel) -> Subdivision:
        return Subdivision(
            code=orm.code,
            country_code=orm.country_code,
            category_code=orm.category_code,
            parent_code=orm.parent_code,
            latitude=orm.latitude,
            longitude=orm.longitude,
        )

    async def get_by_code(self, code: str) -> Subdivision | None:
        orm = await self._session.get(SubdivisionModel, code.upper())
        return self._to_domain(orm) if orm else None

    async def list_by_country(self, country_code: str) -> list[Subdivision]:
        stmt = (
            select(SubdivisionModel)
            .where(
                SubdivisionModel.country_code == country_code.upper(),
                SubdivisionModel.is_active.is_(True),
            )
            .order_by(SubdivisionModel.sort_order)
        )
        result = await self._session.execute(stmt)
        return [self._to_domain(orm) for orm in result.scalars().all()]
