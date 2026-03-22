"""Currency repository — Data Mapper implementation.

Translates between the ``currencies`` ORM table and the domain
:class:`~src.modules.geo.domain.value_objects.Currency` value object.
"""

from sqlalchemy import exists as sa_exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.geo.domain.interfaces import ICurrencyRepository
from src.modules.geo.domain.value_objects import Currency
from src.modules.geo.infrastructure.models import CurrencyModel


class CurrencyRepository(ICurrencyRepository):
    """SQLAlchemy read-only repository for currencies."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @staticmethod
    def _to_domain(orm: CurrencyModel) -> Currency:
        return Currency(
            code=orm.code,
            numeric=orm.numeric,
            name=orm.name,
            minor_unit=orm.minor_unit,
        )

    async def get_by_code(self, code: str) -> Currency | None:
        orm = await self._session.get(CurrencyModel, code.upper())
        return self._to_domain(orm) if orm else None

    async def list_active(self) -> list[Currency]:
        stmt = (
            select(CurrencyModel)
            .where(CurrencyModel.is_active.is_(True))
            .order_by(CurrencyModel.sort_order)
        )
        result = await self._session.execute(stmt)
        return [self._to_domain(orm) for orm in result.scalars().all()]

    async def list_all(self) -> list[Currency]:
        stmt = select(CurrencyModel).order_by(CurrencyModel.sort_order)
        result = await self._session.execute(stmt)
        return [self._to_domain(orm) for orm in result.scalars().all()]

    async def exists(self, code: str) -> bool:
        stmt = sa_exists(
            select(CurrencyModel.code).where(CurrencyModel.code == code.upper())
        ).select()
        result = await self._session.execute(stmt)
        return result.scalar() or False
