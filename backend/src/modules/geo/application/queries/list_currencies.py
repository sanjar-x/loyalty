"""Query handler: list currencies with translations.

CQRS read side — uses ORM select + selectinload for efficient
eager loading of translations. Supports filtering by country.
"""

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.modules.geo.application.queries.read_models import (
    CurrencyListReadModel,
    CurrencyReadModel,
    CurrencyTranslationReadModel,
)
from src.modules.geo.domain.exceptions import CountryNotFoundError
from src.modules.geo.infrastructure.models import (
    CountryCurrencyModel,
    CountryModel,
    CurrencyModel,
)

logger = structlog.get_logger(__name__)


class ListCurrenciesHandler:
    """Fetch currencies with translations.

    Supports two modes:
    - All currencies (when ``country_code`` is ``None``)
    - Currencies for a specific country (validates country exists → 404)
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def handle(
        self,
        lang_code: str | None = None,
        include_inactive: bool = False,
        country_code: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> CurrencyListReadModel:
        if country_code is not None:
            return await self._by_country(country_code, lang_code, offset, limit)
        return await self._all(lang_code, include_inactive, offset, limit)

    async def _all(
        self,
        lang_code: str | None,
        include_inactive: bool,
        offset: int,
        limit: int,
    ) -> CurrencyListReadModel:
        logger.info(
            "list_currencies.start",
            lang_code=lang_code,
            include_inactive=include_inactive,
            offset=offset,
            limit=limit,
        )

        base_where = select(CurrencyModel)
        if not include_inactive:
            base_where = base_where.where(CurrencyModel.is_active.is_(True))

        # Count total (database-side)
        count_stmt = select(func.count()).select_from(base_where.subquery())
        total = (await self._session.execute(count_stmt)).scalar_one()

        # Fetch with translations
        stmt = (
            base_where
            .options(selectinload(CurrencyModel.translations))
            .order_by(CurrencyModel.sort_order, CurrencyModel.code)
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        currencies = result.scalars().unique().all()

        items = [self._to_read_model(orm, lang_code) for orm in currencies]

        logger.info("list_currencies.success", returned=len(items), total=total)
        return CurrencyListReadModel(items=items, total=total)

    async def _by_country(
        self,
        country_code: str,
        lang_code: str | None,
        offset: int,
        limit: int,
    ) -> CurrencyListReadModel:
        code = country_code.upper()
        logger.info(
            "list_country_currencies.start",
            country_code=code,
            lang_code=lang_code,
        )

        # Validate country exists → 404
        country = await self._session.get(CountryModel, code)
        if country is None:
            raise CountryNotFoundError(code)

        # Count total (database-side)
        count_stmt = (
            select(func.count())
            .select_from(CountryCurrencyModel)
            .where(CountryCurrencyModel.country_code == code)
        )
        total = (await self._session.execute(count_stmt)).scalar_one()

        # Fetch currencies linked to country
        stmt = (
            select(CurrencyModel)
            .join(CountryCurrencyModel)
            .where(CountryCurrencyModel.country_code == code)
            .options(selectinload(CurrencyModel.translations))
            .order_by(CountryCurrencyModel.is_primary.desc(), CurrencyModel.code)
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        currencies = result.scalars().unique().all()

        items = [self._to_read_model(orm, lang_code) for orm in currencies]

        logger.info(
            "list_country_currencies.success",
            country_code=code,
            returned=len(items),
            total=total,
        )
        return CurrencyListReadModel(items=items, total=total)

    @staticmethod
    def _to_read_model(
        orm: CurrencyModel,
        lang_code: str | None,
    ) -> CurrencyReadModel:
        translations = [
            CurrencyTranslationReadModel(
                lang_code=tr.lang_code,
                name=tr.name,
            )
            for tr in orm.translations
            if lang_code is None or tr.lang_code == lang_code
        ]

        return CurrencyReadModel(
            code=orm.code,
            numeric=orm.numeric,
            name=orm.name,
            minor_unit=orm.minor_unit,
            translations=translations,
        )
