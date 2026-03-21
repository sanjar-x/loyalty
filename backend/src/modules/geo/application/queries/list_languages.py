"""Query handler: list languages.

Strict CQRS read side — queries the database directly via
AsyncSession + raw SQL and returns a Pydantic read model.
"""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.geo.application.queries.read_models import (
    LanguageListReadModel,
    LanguageReadModel,
)

_LIST_ACTIVE_SQL = text(
    "SELECT code, iso639_1, iso639_2, iso639_3, script, "
    "       name_en, name_native, direction, "
    "       is_active, is_default, sort_order "
    "FROM languages WHERE is_active = true ORDER BY sort_order"
)

_LIST_ALL_SQL = text(
    "SELECT code, iso639_1, iso639_2, iso639_3, script, "
    "       name_en, name_native, direction, "
    "       is_active, is_default, sort_order "
    "FROM languages ORDER BY sort_order"
)


def _to_read_model(row: dict) -> LanguageReadModel:
    return LanguageReadModel(
        code=row["code"],
        iso639_1=row["iso639_1"],
        iso639_2=row["iso639_2"],
        iso639_3=row["iso639_3"],
        script=row["script"],
        name_en=row["name_en"],
        name_native=row["name_native"],
        direction=row["direction"],
        is_active=row["is_active"],
        is_default=row["is_default"],
        sort_order=row["sort_order"],
    )


class ListLanguagesHandler:
    """Fetch languages (active only or all)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def handle(self, *, include_inactive: bool = False) -> LanguageListReadModel:
        sql = _LIST_ALL_SQL if include_inactive else _LIST_ACTIVE_SQL
        result = await self._session.execute(sql)
        items = [_to_read_model(row) for row in result.mappings().all()]
        return LanguageListReadModel(items=items, total=len(items))
