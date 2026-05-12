"""Query handler: get a single currency with translations.

CQRS read side — uses ORM get + selectinload for efficient
eager loading of translations.
"""

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.modules.geo.application.queries.read_models import (
    CurrencyReadModel,
    CurrencyTranslationReadModel,
)
from src.modules.geo.domain.exceptions import CurrencyNotFoundError
from src.modules.geo.infrastructure.models import CurrencyModel

logger = structlog.get_logger(__name__)


class GetCurrencyHandler:
    """Fetch a single currency by ISO 4217 alpha-3 code with translations."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def handle(
        self,
        code: str,
        lang_code: str | None = None,
    ) -> CurrencyReadModel:
        currency_code = code.upper()
        logger.info("get_currency.start", code=currency_code, lang_code=lang_code)

        stmt = (
            select(CurrencyModel)
            .where(CurrencyModel.code == currency_code)
            .options(selectinload(CurrencyModel.translations))
        )
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()

        if orm is None:
            raise CurrencyNotFoundError(currency_code)

        translations = [
            CurrencyTranslationReadModel(
                lang_code=tr.lang_code,
                name=tr.name,
            )
            for tr in orm.translations
            if lang_code is None or tr.lang_code == lang_code
        ]

        logger.info("get_currency.success", code=currency_code)
        return CurrencyReadModel(
            code=orm.code,
            numeric=orm.numeric,
            name=orm.name,
            minor_unit=orm.minor_unit,
            is_active=orm.is_active,
            sort_order=orm.sort_order,
            translations=translations,
        )
