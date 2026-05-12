"""Query handler: get a single country with translations.

CQRS read side — uses ORM get + selectinload for efficient
eager loading of translations.
"""

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.modules.geo.application.queries.read_models import (
    CountryReadModel,
    CountryTranslationReadModel,
)
from src.modules.geo.domain.exceptions import CountryNotFoundError
from src.modules.geo.infrastructure.models import CountryModel

logger = structlog.get_logger(__name__)


class GetCountryHandler:
    """Fetch a single country by Alpha-2 code with translations."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def handle(
        self,
        alpha2: str,
        lang_code: str | None = None,
    ) -> CountryReadModel:
        code = alpha2.upper()
        logger.info("get_country.start", alpha2=code, lang_code=lang_code)

        stmt = (
            select(CountryModel)
            .where(CountryModel.alpha2 == code)
            .options(selectinload(CountryModel.translations))
        )
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()

        if orm is None:
            raise CountryNotFoundError(code)

        translations = [
            CountryTranslationReadModel(
                lang_code=tr.lang_code,
                name=tr.name,
                official_name=tr.official_name,
            )
            for tr in orm.translations
            if lang_code is None or tr.lang_code == lang_code
        ]

        logger.info("get_country.success", alpha2=code)
        return CountryReadModel(
            alpha2=orm.alpha2,
            alpha3=orm.alpha3,
            numeric=orm.numeric,
            translations=translations,
        )
