"""Query handler: list subdivisions for a country with translations.

CQRS read side — uses ORM select + selectinload for efficient
eager loading of translations.
"""

import structlog
from sqlalchemy import ColumnElement, func, select
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
    SubdivisionTranslationModel,
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
        search: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> SubdivisionListReadModel:
        code = country_code.upper()
        logger.info(
            "list_subdivisions.start",
            country_code=code,
            lang_code=lang_code,
            search=search,
            offset=offset,
            limit=limit,
        )

        # Validate country exists → 404
        country = await self._session.get(CountryModel, code)
        if country is None:
            raise CountryNotFoundError(code)

        # Base filters
        base_filters = [
            SubdivisionModel.country_code == code,
            SubdivisionModel.is_active.is_(True),
        ]

        # When searching by translated name, JOIN on translations and ILIKE
        search_term = search.strip() if search is not None else ""
        search_join = bool(search_term)
        if search_join:
            pattern = f"%{search_term}%"
            translation_filters: list[ColumnElement[bool]] = [
                SubdivisionTranslationModel.name.ilike(pattern),
            ]
            if lang_code is not None:
                translation_filters.append(
                    SubdivisionTranslationModel.lang_code == lang_code,
                )

        # Count total (database-side)
        count_stmt = (
            select(func.count()).select_from(SubdivisionModel).where(*base_filters)
        )
        if search_join:
            count_stmt = count_stmt.join(
                SubdivisionTranslationModel,
                SubdivisionModel.code == SubdivisionTranslationModel.subdivision_code,
            ).where(*translation_filters)
        total = (await self._session.execute(count_stmt)).scalar_one()

        # Fetch with translations
        stmt = (
            select(SubdivisionModel)
            .where(*base_filters)
            .options(selectinload(SubdivisionModel.translations))
            .order_by(SubdivisionModel.sort_order, SubdivisionModel.code)
            .offset(offset)
            .limit(limit)
        )
        if search_join:
            stmt = stmt.join(
                SubdivisionTranslationModel,
                SubdivisionModel.code == SubdivisionTranslationModel.subdivision_code,
            ).where(*translation_filters)
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
            type_code=orm.type_code,
            parent_code=orm.parent_code,
            latitude=float(orm.latitude) if orm.latitude is not None else None,
            longitude=float(orm.longitude) if orm.longitude is not None else None,
            is_active=orm.is_active,
            sort_order=orm.sort_order,
            translations=translations,
        )
