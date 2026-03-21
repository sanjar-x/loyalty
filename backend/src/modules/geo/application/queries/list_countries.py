"""Query handler: list all countries with translations.

Strict CQRS read side — queries the database directly via
AsyncSession + raw SQL and returns a Pydantic read model.
"""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.geo.application.queries.read_models import (
    CountryListReadModel,
    CountryReadModel,
    CountryTranslationReadModel,
)

_LIST_COUNTRIES_SQL = text(
    "SELECT alpha2, alpha3, numeric, name "
    "FROM countries ORDER BY name"
)

_TRANSLATIONS_SQL = text(
    "SELECT country_code, lang_code, name, official_name "
    "FROM country_translations ORDER BY country_code, lang_code"
)

_TRANSLATIONS_FOR_LANG_SQL = text(
    "SELECT country_code, lang_code, name, official_name "
    "FROM country_translations "
    "WHERE lang_code = :lang_code "
    "ORDER BY country_code"
)


class ListCountriesHandler:
    """Fetch all countries with translations."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def handle(self, lang_code: str | None = None) -> CountryListReadModel:
        result = await self._session.execute(_LIST_COUNTRIES_SQL)
        countries = result.mappings().all()

        if lang_code:
            tr_result = await self._session.execute(
                _TRANSLATIONS_FOR_LANG_SQL, {"lang_code": lang_code},
            )
        else:
            tr_result = await self._session.execute(_TRANSLATIONS_SQL)

        tr_map: dict[str, list[CountryTranslationReadModel]] = {}
        for tr in tr_result.mappings().all():
            tr_map.setdefault(tr["country_code"], []).append(
                CountryTranslationReadModel(
                    lang_code=tr["lang_code"],
                    name=tr["name"],
                    official_name=tr["official_name"],
                )
            )

        items = [
            CountryReadModel(
                alpha2=c["alpha2"],
                alpha3=c["alpha3"],
                numeric=c["numeric"],
                name=c["name"],
                translations=tr_map.get(c["alpha2"], []),
            )
            for c in countries
        ]

        return CountryListReadModel(items=items, total=len(items))
