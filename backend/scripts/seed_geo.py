"""Seed geo reference data from JSON files.

Loads:
1. ``seed_geo_subdivision_types.json`` — global subdivision types + translations
2. ``seed_geo_russia.json`` — Russia country, currencies link, subdivision types,
   and all 83 subdivisions with translations

Idempotent: uses INSERT ... ON CONFLICT DO NOTHING / DO UPDATE for all rows.

Usage::

    uv run python scripts/seed_geo.py
"""

# Ensure the project root is on sys.path so ``src.*`` imports resolve.
from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

import structlog
from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))
load_dotenv(_PROJECT_ROOT / ".env", override=False)
structlog.configure(
    processors=[
        structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(0),
)
logger = structlog.get_logger("seed_geo")


def _build_database_url(target: str = "dev") -> str:
    """Build a ``postgresql+asyncpg://`` URL.

    *target*: ``"dev"`` → ``DEV_PG*`` env vars (local Docker),
              ``"railway"`` → ``PG*`` env vars (remote Railway).
    """
    if target == "dev":
        user = os.getenv("DEV_PGUSER", "postgres")
        password = os.getenv("DEV_PGPASSWORD", "postgres")
        host = os.getenv("DEV_PGHOST", "127.0.0.1")
        port = os.getenv("DEV_PGPORT", "5432")
        db = os.getenv("DEV_PGDATABASE", "enterprise")
    else:
        user = os.getenv("PGUSER", "postgres")
        password = os.getenv("PGPASSWORD", "")
        host = os.getenv("PGHOST", "localhost")
        port = os.getenv("PGPORT", "5432")
        db = os.getenv("PGDATABASE", "railway")
    return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{db}"


SCRIPTS_DIR = Path(__file__).resolve().parent


# ---------------------------------------------------------------------------
#  Helpers
# ---------------------------------------------------------------------------


async def _ensure_languages(session: AsyncSession) -> None:
    """Insert prerequisite languages (en, ru) if they don't exist."""
    for lang in [
        {
            "code": "en",
            "iso639_1": "en",
            "iso639_2": "eng",
            "iso639_3": "eng",
            "script": "Latn",
            "name_en": "English",
            "name_native": "English",
            "direction": "ltr",
            "is_active": True,
            "is_default": False,
            "sort_order": 2,
        },
        {
            "code": "ru",
            "iso639_1": "ru",
            "iso639_2": "rus",
            "iso639_3": "rus",
            "script": "Cyrl",
            "name_en": "Russian",
            "name_native": "Русский",
            "direction": "ltr",
            "is_active": True,
            "is_default": True,
            "sort_order": 1,
        },
    ]:
        await session.execute(
            text("""
                INSERT INTO languages
                    (code, iso639_1, iso639_2, iso639_3, script,
                     name_en, name_native, direction, is_active, is_default, sort_order)
                VALUES (:code, :iso639_1, :iso639_2, :iso639_3, :script,
                        :name_en, :name_native, :direction, :is_active, :is_default, :sort_order)
                ON CONFLICT (code) DO NOTHING
            """),
            lang,
        )


async def _upsert_subdivision_type(
    session: AsyncSession,
    code: str,
    sort_order: int,
    translations: list[dict],
) -> None:
    """Insert or update a subdivision type and its translations."""
    await session.execute(
        text("""
            INSERT INTO subdivision_types (code, sort_order)
            VALUES (:code, :sort_order)
            ON CONFLICT (code) DO UPDATE SET sort_order = EXCLUDED.sort_order
        """),
        {"code": code, "sort_order": sort_order},
    )

    for tr in translations:
        await session.execute(
            text("""
                INSERT INTO subdivision_type_translations (id, type_code, lang_code, name)
                VALUES (gen_random_uuid(), :type_code, :lang_code, :name)
                ON CONFLICT ON CONSTRAINT uq_sub_type_lang
                DO UPDATE SET name = EXCLUDED.name
            """),
            {"type_code": code, "lang_code": tr["lang_code"], "name": tr["name"]},
        )


async def _upsert_country(
    session: AsyncSession,
    alpha2: str,
    alpha3: str,
    numeric: str,
) -> None:
    await session.execute(
        text("""
            INSERT INTO countries (alpha2, alpha3, numeric)
            VALUES (:alpha2, :alpha3, :numeric)
            ON CONFLICT (alpha2) DO UPDATE
                SET alpha3 = EXCLUDED.alpha3, numeric = EXCLUDED.numeric
        """),
        {"alpha2": alpha2, "alpha3": alpha3, "numeric": numeric},
    )


async def _upsert_country_translations(
    session: AsyncSession,
    country_code: str,
    translations: list[dict],
) -> None:
    for tr in translations:
        await session.execute(
            text("""
                INSERT INTO country_translations
                    (id, country_code, lang_code, name, official_name)
                VALUES (gen_random_uuid(), :cc, :lc, :name, :official_name)
                ON CONFLICT ON CONSTRAINT uq_country_lang
                DO UPDATE SET name = EXCLUDED.name,
                              official_name = EXCLUDED.official_name
            """),
            {
                "cc": country_code,
                "lc": tr["lang_code"],
                "name": tr["name"],
                "official_name": tr.get("official_name"),
            },
        )


async def _upsert_country_currencies(
    session: AsyncSession,
    country_code: str,
    currencies: list[dict],
) -> None:
    for c in currencies:
        await session.execute(
            text("""
                INSERT INTO country_currencies (country_code, currency_code, is_primary)
                VALUES (:cc, :cur, :is_primary)
                ON CONFLICT (country_code, currency_code)
                DO UPDATE SET is_primary = EXCLUDED.is_primary
            """),
            {
                "cc": country_code,
                "cur": c["currency_code"],
                "is_primary": c.get("is_primary", False),
            },
        )


async def _upsert_subdivision(
    session: AsyncSession,
    code: str,
    country_code: str,
    type_code: str,
    sort_order: int,
    translations: list[dict],
) -> None:
    await session.execute(
        text("""
            INSERT INTO subdivisions
                (code, country_code, type_code, sort_order, is_active)
            VALUES (:code, :cc, :tc, :sort_order, true)
            ON CONFLICT (code) DO UPDATE
                SET type_code = EXCLUDED.type_code,
                    sort_order = EXCLUDED.sort_order
        """),
        {
            "code": code,
            "cc": country_code,
            "tc": type_code,
            "sort_order": sort_order,
        },
    )

    for tr in translations:
        await session.execute(
            text("""
                INSERT INTO subdivision_translations
                    (id, subdivision_code, lang_code, name, official_name, local_variant)
                VALUES (gen_random_uuid(), :sc, :lc, :name, :official_name, :local_variant)
                ON CONFLICT ON CONSTRAINT uq_subdivision_lang
                DO UPDATE SET name = EXCLUDED.name,
                              official_name = EXCLUDED.official_name,
                              local_variant = EXCLUDED.local_variant
            """),
            {
                "sc": code,
                "lc": tr["lang_code"],
                "name": tr["name"],
                "official_name": tr.get("official_name"),
                "local_variant": tr.get("local_variant"),
            },
        )


# ---------------------------------------------------------------------------
#  Main
# ---------------------------------------------------------------------------


async def seed() -> None:
    target = sys.argv[1] if len(sys.argv) > 1 else "dev"
    if target not in ("dev", "railway"):
        print(f"Usage: {sys.argv[0]} [dev|railway]")
        raise SystemExit(2)

    engine = create_async_engine(url=_build_database_url(target), echo=False)

    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("db.connected")
    except Exception as e:
        logger.error("db.unreachable", error=str(e))
        raise SystemExit(1) from e

    # ── 0. Prerequisites: languages ─────────────────────────────────
    async with engine.begin() as conn:
        session = AsyncSession(bind=conn, expire_on_commit=False)
        await _ensure_languages(session)
    logger.info("languages.ensured")

    # ── 1. Subdivision types (global) ────────────────────────────────
    types_file = SCRIPTS_DIR / "seed_geo_subdivision_types.json"
    if types_file.exists():
        types_data: list[dict] = json.loads(types_file.read_text("utf-8"))
        async with engine.begin() as conn:
            session = AsyncSession(bind=conn, expire_on_commit=False)
            for st in types_data:
                await _upsert_subdivision_type(
                    session,
                    code=st["code"],
                    sort_order=st.get("sort_order", 0),
                    translations=st.get("translations", []),
                )
        logger.info(
            "subdivision_types.seeded",
            count=len(types_data),
        )
    else:
        logger.warning("subdivision_types.file_missing", path=str(types_file))

    # ── 2. Russia (country + subdivision types + subdivisions) ───────
    russia_file = SCRIPTS_DIR / "seed_geo_russia.json"
    if russia_file.exists():
        data: dict = json.loads(russia_file.read_text("utf-8"))

        async with engine.begin() as conn:
            session = AsyncSession(bind=conn, expire_on_commit=False)

            # 2a. Country
            c = data["country"]
            await _upsert_country(session, c["alpha2"], c["alpha3"], c["numeric"])
            logger.info("country.seeded", alpha2=c["alpha2"])

            # 2b. Country translations
            await _upsert_country_translations(
                session, c["alpha2"], data.get("country_translations", [])
            )

            # 2c. Country currencies
            await _upsert_country_currencies(
                session, c["alpha2"], data.get("country_currencies", [])
            )

            # 2d. Subdivision types (country-specific, may overlap with global)
            for st in data.get("subdivision_types", []):
                await _upsert_subdivision_type(
                    session,
                    code=st["code"],
                    sort_order=st.get("sort_order", 0),
                    translations=st.get("translations", []),
                )

            # 2e. Subdivisions
            subdivisions = data.get("subdivisions", [])
            for sub in subdivisions:
                await _upsert_subdivision(
                    session,
                    code=sub["code"],
                    country_code=c["alpha2"],
                    type_code=sub["type_code"],
                    sort_order=sub.get("sort_order", 0),
                    translations=sub.get("translations", []),
                )

            logger.info("russia.seeded", subdivisions=len(subdivisions))
    else:
        logger.warning("russia.file_missing", path=str(russia_file))

    await engine.dispose()
    logger.info("seed_geo.done")


if __name__ == "__main__":
    asyncio.run(seed())
