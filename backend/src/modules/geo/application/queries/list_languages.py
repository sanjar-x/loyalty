"""Query handler: list languages.

CQRS read side — uses ORM select for language listing.
"""

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.geo.application.queries.read_models import (
    LanguageListReadModel,
    LanguageReadModel,
)
from src.modules.geo.infrastructure.models import LanguageModel

logger = structlog.get_logger(__name__)


class ListLanguagesHandler:
    """Fetch languages (active only or all)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def handle(
        self,
        *,
        include_inactive: bool = False,
        offset: int = 0,
        limit: int = 50,
    ) -> LanguageListReadModel:
        logger.info(
            "list_languages.start",
            include_inactive=include_inactive,
            offset=offset,
            limit=limit,
        )

        base_where = select(LanguageModel)
        if not include_inactive:
            base_where = base_where.where(LanguageModel.is_active.is_(True))

        # Count total (database-side)
        count_stmt = select(func.count()).select_from(base_where.subquery())
        total = (await self._session.execute(count_stmt)).scalar_one()

        # Fetch paginated
        stmt = base_where.order_by(LanguageModel.sort_order).offset(offset).limit(limit)
        result = await self._session.execute(stmt)
        languages = result.scalars().all()

        items = [self._to_read_model(orm) for orm in languages]

        logger.info("list_languages.success", returned=len(items), total=total)
        return LanguageListReadModel(items=items, total=total)

    @staticmethod
    def _to_read_model(orm: LanguageModel) -> LanguageReadModel:
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
