"""Country repository — Data Mapper implementation.

Translates between the ``countries`` ORM table and the domain
:class:`~src.modules.geo.domain.value_objects.Country` value object.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.geo.domain.interfaces import ICountryRepository
from src.modules.geo.domain.value_objects import Country
from src.modules.geo.infrastructure.models import CountryModel


class CountryRepository(ICountryRepository):
    """SQLAlchemy read-only repository for countries."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @staticmethod
    def _to_domain(orm: CountryModel) -> Country:
        return Country(
            alpha2=orm.alpha2,
            alpha3=orm.alpha3,
            numeric=orm.numeric,
        )

    async def get_by_alpha2(self, alpha2: str) -> Country | None:
        orm = await self._session.get(CountryModel, alpha2.upper())
        return self._to_domain(orm) if orm else None

    async def get_by_alpha3(self, alpha3: str) -> Country | None:
        stmt = (
            select(CountryModel).where(CountryModel.alpha3 == alpha3.upper()).limit(1)
        )
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    async def list_all(self) -> list[Country]:
        stmt = select(CountryModel).order_by(CountryModel.alpha2)
        result = await self._session.execute(stmt)
        return [self._to_domain(orm) for orm in result.scalars().all()]
