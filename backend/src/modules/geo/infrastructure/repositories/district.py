"""District repository — Data Mapper implementation.

Translates between the ``districts`` ORM table and the domain
:class:`~src.modules.geo.domain.value_objects.District` value object.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.geo.domain.interfaces import IDistrictRepository
from src.modules.geo.domain.value_objects import District
from src.modules.geo.infrastructure.models import DistrictModel


class DistrictRepository(IDistrictRepository):
    """SQLAlchemy read-only repository for districts."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @staticmethod
    def _to_domain(orm: DistrictModel) -> District:
        return District(
            id=str(orm.id),
            subdivision_code=orm.subdivision_code,
            type_code=orm.type_code,
            oktmo_prefix=orm.oktmo_prefix,
            fias_guid=str(orm.fias_guid) if orm.fias_guid is not None else None,
            latitude=orm.latitude,
            longitude=orm.longitude,
        )

    async def get_by_id(self, district_id: str) -> District | None:
        orm = await self._session.get(DistrictModel, district_id)
        return self._to_domain(orm) if orm else None

    async def list_by_subdivision(self, subdivision_code: str) -> list[District]:
        stmt = (
            select(DistrictModel)
            .where(
                DistrictModel.subdivision_code == subdivision_code.upper(),
                DistrictModel.is_active.is_(True),
            )
            .order_by(DistrictModel.sort_order)
        )
        result = await self._session.execute(stmt)
        return [self._to_domain(orm) for orm in result.scalars().all()]

    async def get_by_oktmo_prefix(self, oktmo_prefix: str) -> District | None:
        stmt = select(DistrictModel).where(
            DistrictModel.oktmo_prefix == oktmo_prefix
        )
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    async def get_by_fias_guid(self, fias_guid: str) -> District | None:
        stmt = select(DistrictModel).where(
            DistrictModel.fias_guid == fias_guid
        )
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None
