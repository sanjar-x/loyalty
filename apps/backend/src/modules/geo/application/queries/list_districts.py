"""Query handler: list districts for a subdivision with translations.

CQRS read side — uses ORM select + selectinload for efficient
eager loading of translations.
"""

import structlog
from sqlalchemy import ColumnElement, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.modules.geo.application.queries.read_models import (
    DistrictListReadModel,
    DistrictReadModel,
    DistrictTranslationReadModel,
)
from src.modules.geo.domain.exceptions import SubdivisionNotFoundError
from src.modules.geo.infrastructure.models import (
    DistrictModel,
    DistrictTranslationModel,
    SubdivisionModel,
)

logger = structlog.get_logger(__name__)


class ListDistrictsHandler:
    """Fetch districts for a subdivision with translations."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def handle(
        self,
        subdivision_code: str,
        lang_code: str | None = None,
        search: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> DistrictListReadModel:
        code = subdivision_code.upper()
        logger.info(
            "list_districts.start",
            subdivision_code=code,
            lang_code=lang_code,
            search=search,
            offset=offset,
            limit=limit,
        )

        # Validate subdivision exists → 404
        subdivision = await self._session.get(SubdivisionModel, code)
        if subdivision is None:
            raise SubdivisionNotFoundError(code)

        # Base filters
        base_filters = [
            DistrictModel.subdivision_code == code,
            DistrictModel.is_active.is_(True),
        ]

        # When searching by translated name, JOIN on translations and ILIKE
        search_term = search.strip() if search is not None else ""
        search_join = bool(search_term)
        if search_join:
            pattern = f"%{search_term}%"
            translation_filters: list[ColumnElement[bool]] = [
                DistrictTranslationModel.name.ilike(pattern),
            ]
            if lang_code is not None:
                translation_filters.append(
                    DistrictTranslationModel.lang_code == lang_code,
                )

        # Count total (database-side)
        count_stmt = (
            select(func.count()).select_from(DistrictModel).where(*base_filters)
        )
        if search_join:
            count_stmt = count_stmt.join(
                DistrictTranslationModel,
                DistrictModel.id == DistrictTranslationModel.district_id,
            ).where(*translation_filters)
        total = (await self._session.execute(count_stmt)).scalar_one()

        # Fetch with translations
        stmt = (
            select(DistrictModel)
            .where(*base_filters)
            .options(selectinload(DistrictModel.translations))
            .order_by(DistrictModel.sort_order, DistrictModel.id)
            .offset(offset)
            .limit(limit)
        )
        if search_join:
            stmt = stmt.join(
                DistrictTranslationModel,
                DistrictModel.id == DistrictTranslationModel.district_id,
            ).where(*translation_filters)
        result = await self._session.execute(stmt)
        districts = result.scalars().unique().all()

        items = [self._to_read_model(orm, lang_code) for orm in districts]

        logger.info(
            "list_districts.success",
            subdivision_code=code,
            returned=len(items),
            total=total,
        )
        return DistrictListReadModel(items=items, total=total)

    @staticmethod
    def _to_read_model(
        orm: DistrictModel,
        lang_code: str | None,
    ) -> DistrictReadModel:
        translations = [
            DistrictTranslationReadModel(
                lang_code=tr.lang_code,
                name=tr.name,
                official_name=tr.official_name,
                local_variant=tr.local_variant,
            )
            for tr in orm.translations
            if lang_code is None or tr.lang_code == lang_code
        ]

        return DistrictReadModel(
            id=str(orm.id),
            subdivision_code=orm.subdivision_code,
            type_code=orm.type_code,
            oktmo_prefix=orm.oktmo_prefix,
            fias_guid=str(orm.fias_guid) if orm.fias_guid is not None else None,
            latitude=float(orm.latitude) if orm.latitude is not None else None,
            longitude=float(orm.longitude) if orm.longitude is not None else None,
            is_active=orm.is_active,
            sort_order=orm.sort_order,
            translations=translations,
        )
