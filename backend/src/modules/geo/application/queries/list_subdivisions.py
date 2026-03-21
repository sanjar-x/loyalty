"""Query handler: list subdivisions for a country with translations.

Strict CQRS read side — queries the database directly via
AsyncSession + raw SQL and returns a Pydantic read model.
"""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.geo.application.queries.read_models import (
    SubdivisionListReadModel,
    SubdivisionReadModel,
    SubdivisionTranslationReadModel,
)

_LIST_WITH_TRANSLATIONS_SQL = text(
    "SELECT s.code, s.country_code, s.category_code, s.parent_code, "
    "       s.latitude, s.longitude, "
    "       t.lang_code AS tr_lang, t.name AS tr_name, "
    "       t.official_name AS tr_official, t.local_variant AS tr_local "
    "FROM subdivisions s "
    "LEFT JOIN subdivision_translations t ON t.subdivision_code = s.code "
    "WHERE s.country_code = :country_code AND s.is_active = true "
    "ORDER BY s.sort_order, s.code, t.lang_code"
)

_LIST_WITH_TRANSLATIONS_FOR_LANG_SQL = text(
    "SELECT s.code, s.country_code, s.category_code, s.parent_code, "
    "       s.latitude, s.longitude, "
    "       t.lang_code AS tr_lang, t.name AS tr_name, "
    "       t.official_name AS tr_official, t.local_variant AS tr_local "
    "FROM subdivisions s "
    "LEFT JOIN subdivision_translations t "
    "  ON t.subdivision_code = s.code AND t.lang_code = :lang_code "
    "WHERE s.country_code = :country_code AND s.is_active = true "
    "ORDER BY s.sort_order, s.code"
)


class ListSubdivisionsHandler:
    """Fetch subdivisions for a country with translations in one query."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def handle(
        self, country_code: str, lang_code: str | None = None,
    ) -> SubdivisionListReadModel:
        params: dict = {"country_code": country_code.upper()}

        if lang_code:
            params["lang_code"] = lang_code
            result = await self._session.execute(
                _LIST_WITH_TRANSLATIONS_FOR_LANG_SQL, params,
            )
        else:
            result = await self._session.execute(
                _LIST_WITH_TRANSLATIONS_SQL, params,
            )

        subdivisions: dict[str, SubdivisionReadModel] = {}
        for row in result.mappings().all():
            code = row["code"]
            if code not in subdivisions:
                subdivisions[code] = SubdivisionReadModel(
                    code=code,
                    country_code=row["country_code"],
                    category_code=row["category_code"],
                    parent_code=row["parent_code"],
                    latitude=float(row["latitude"]) if row["latitude"] is not None else None,
                    longitude=float(row["longitude"]) if row["longitude"] is not None else None,
                )
            if row["tr_lang"] is not None:
                subdivisions[code].translations.append(
                    SubdivisionTranslationReadModel(
                        lang_code=row["tr_lang"],
                        name=row["tr_name"],
                        official_name=row["tr_official"],
                        local_variant=row["tr_local"],
                    )
                )

        items = list(subdivisions.values())
        return SubdivisionListReadModel(items=items, total=len(items))
