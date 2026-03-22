"""Query handler: list subdivisions for a country with translations.

CQRS read side — uses ORM select + selectinload for efficient
eager loading of translations.
"""

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.modules.geo.application.queries.read_models import (
    SubdivisionListReadModel,
    SubdivisionReadModel,
    SubdivisionTranslationReadModel,
)
from src.modules.geo.domain.exceptions import CountryNotFoundError
from src.modules.geo.infrastructure.models import (
    CountryModel,
    SubdivisionModel,
)

logger = structlog.get_logger(__name__)


class ListSubdivisionsHandler:
    """Fetch subdivisions for a country with translations."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def handle(
        self,
        country_code: str,
        lang_code: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> SubdivisionListReadModel:
        code = country_code.upper()
        logger.info(
            "list_subdivisions.start",
            country_code=code,
            lang_code=lang_code,
            offset=offset,
            limit=limit,
        )

        # Validate country exists → 404
        country = await self._session.get(CountryModel, code)
        if country is None:
            raise CountryNotFoundError(code)

        # Count total (database-side)
        count_stmt = (
            select(func.count())
            .select_from(SubdivisionModel)
            .where(
                SubdivisionModel.country_code == code,
                SubdivisionModel.is_active.is_(True),
            )
        )
        total = (await self._session.execute(count_stmt)).scalar_one()

        # Fetch with translations
        stmt = (
            select(SubdivisionModel)
            .where(
                SubdivisionModel.country_code == code,
                SubdivisionModel.is_active.is_(True),
            )
            .options(selectinload(SubdivisionModel.translations))
            .order_by(SubdivisionModel.sort_order, SubdivisionModel.code)
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        subdivisions = result.scalars().unique().all()

        items = [self._to_read_model(orm, lang_code) for orm in subdivisions]

        logger.info(
            "list_subdivisions.success",
            country_code=code,
            returned=len(items),
            total=total,
        )
        return SubdivisionListReadModel(items=items, total=total)

    @staticmethod
    def _to_read_model(
        orm: SubdivisionModel,
        lang_code: str | None,
    ) -> SubdivisionReadModel:
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

        return SubdivisionReadModel(
            code=orm.code,
            country_code=orm.country_code,
            category_code=orm.category_code,
            parent_code=orm.parent_code,
            latitude=float(orm.latitude) if orm.latitude is not None else None,
            longitude=float(orm.longitude) if orm.longitude is not None else None,
            translations=translations,
        )
