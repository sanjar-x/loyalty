"""Query handler: get a single subdivision with translations.

CQRS read side — uses ORM get + selectinload for efficient
eager loading of translations.
"""

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.modules.geo.application.queries.read_models import (
    SubdivisionReadModel,
    SubdivisionTranslationReadModel,
)
from src.modules.geo.domain.exceptions import SubdivisionNotFoundError
from src.modules.geo.infrastructure.models import SubdivisionModel

logger = structlog.get_logger(__name__)


class GetSubdivisionHandler:
    """Fetch a single subdivision by ISO 3166-2 code with translations."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def handle(
        self,
        code: str,
        lang_code: str | None = None,
    ) -> SubdivisionReadModel:
        subdivision_code = code.upper()
        logger.info(
            "get_subdivision.start",
            code=subdivision_code,
            lang_code=lang_code,
        )

        stmt = (
            select(SubdivisionModel)
            .where(SubdivisionModel.code == subdivision_code)
            .options(selectinload(SubdivisionModel.translations))
        )
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()

        if orm is None:
            raise SubdivisionNotFoundError(subdivision_code)

        translations = [
            SubdivisionTranslationReadModel(
                lang_code=tr.lang_code,
                name=tr.name,
                official_name=tr.official_name,
                local_variant=tr.local_variant,
            )
            for tr in orm.translations
            if lang_code is None or tr.lang_code == lang_code
        ]

        logger.info("get_subdivision.success", code=subdivision_code)
        return SubdivisionReadModel(
            code=orm.code,
            country_code=orm.country_code,
            type_code=orm.type_code,
            parent_code=orm.parent_code,
            latitude=float(orm.latitude) if orm.latitude is not None else None,
            longitude=float(orm.longitude) if orm.longitude is not None else None,
            is_active=orm.is_active,
            sort_order=orm.sort_order,
            translations=translations,
        )
