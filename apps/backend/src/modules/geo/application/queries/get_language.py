"""Query handler: get a single language by BCP 47 code.

CQRS read side — direct ORM lookup.
"""

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.geo.application.queries.read_models import LanguageReadModel
from src.modules.geo.domain.exceptions import LanguageNotFoundError
from src.modules.geo.infrastructure.models import LanguageModel

logger = structlog.get_logger(__name__)


class GetLanguageHandler:
    """Fetch a single language by its IETF BCP 47 code."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def handle(self, code: str) -> LanguageReadModel:
        logger.info("get_language.start", code=code)

        orm = await self._session.get(LanguageModel, code)

        if orm is None:
            raise LanguageNotFoundError(code)

        logger.info("get_language.success", code=code)
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
