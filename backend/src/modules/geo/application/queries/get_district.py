"""Query handler: get a single district with translations.

CQRS read side — uses ORM get + selectinload for efficient
eager loading of translations.
"""

import uuid as uuid_mod

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.modules.geo.application.queries.read_models import (
    DistrictReadModel,
    DistrictTranslationReadModel,
)
from src.modules.geo.domain.exceptions import DistrictNotFoundError
from src.modules.geo.infrastructure.models import DistrictModel

logger = structlog.get_logger(__name__)


class GetDistrictHandler:
    """Fetch a single district by UUID with translations."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def handle(
        self,
        district_id: str,
        lang_code: str | None = None,
    ) -> DistrictReadModel:
        logger.info(
            "get_district.start",
            district_id=district_id,
            lang_code=lang_code,
        )

        try:
            parsed_id = uuid_mod.UUID(district_id)
        except ValueError:
            raise DistrictNotFoundError(district_id) from None

        stmt = (
            select(DistrictModel)
            .where(DistrictModel.id == parsed_id)
            .options(selectinload(DistrictModel.translations))
        )
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()

        if orm is None:
            raise DistrictNotFoundError(district_id)

        logger.info("get_district.success", district_id=district_id)
        return self._to_read_model(orm, lang_code)

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
