"""Query handler: list all countries with translations.

CQRS read side — uses ORM select + selectinload for efficient
eager loading of translations.
"""

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.modules.geo.application.queries.read_models import (
    CountryListReadModel,
    CountryReadModel,
    CountryTranslationReadModel,
)
from src.modules.geo.infrastructure.models import (
    CountryModel,
    CountryTranslationModel,
)

logger = structlog.get_logger(__name__)


class ListCountriesHandler:
    """Fetch all countries with translations."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def handle(
        self,
        lang_code: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> CountryListReadModel:
        logger.info(
            "list_countries.start",
            lang_code=lang_code,
            offset=offset,
            limit=limit,
        )

        # Count total (database-side)
        count_stmt = select(func.count()).select_from(CountryModel)
        total = (await self._session.execute(count_stmt)).scalar_one()

        # Fetch with translations
        stmt = (
            select(CountryModel)
            .options(selectinload(CountryModel.translations))
            .order_by(CountryModel.alpha2)
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        countries = result.scalars().unique().all()

        items = [self._to_read_model(orm, lang_code) for orm in countries]

        logger.info(
            "list_countries.success",
            returned=len(items),
            total=total,
        )

        return CountryListReadModel(items=items, total=total)

    @staticmethod
    def _to_read_model(
        orm: CountryModel,
        lang_code: str | None,
    ) -> CountryReadModel:
        translations = [
            CountryTranslationReadModel(
                lang_code=tr.lang_code,
                name=tr.name,
                official_name=tr.official_name,
            )
            for tr in orm.translations
            if lang_code is None or tr.lang_code == lang_code
        ]

        return CountryReadModel(
            alpha2=orm.alpha2,
            alpha3=orm.alpha3,
            numeric=orm.numeric,
            translations=translations,
        )
