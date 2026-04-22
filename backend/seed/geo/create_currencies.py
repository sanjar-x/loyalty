"""Seed minimal currency data required by product variants and SKUs.

Uses direct DB connection (no HTTP API for currencies).
Data source: ``seed/geo/currencies.json``.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import TYPE_CHECKING

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

if TYPE_CHECKING:
    from seed.main import SeedContext

_DATA_FILE = Path(__file__).parent / "currencies.json"

UPSERT = text(
    "INSERT INTO currencies (code, numeric, name, minor_unit, is_active) "
    "VALUES (:code, :numeric, :name, :minor_unit, true) "
    "ON CONFLICT (code) DO NOTHING"
)


def _load() -> list[dict]:
    return json.loads(_DATA_FILE.read_text(encoding="utf-8"))


async def _run(db_url: str, rows: list[dict]) -> int:
    engine = create_async_engine(db_url, echo=False)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    created = 0
    async with factory() as s, s.begin():
        for row in rows:
            r = await s.execute(UPSERT, row)
            if r.rowcount and r.rowcount > 0:
                created += 1
    await engine.dispose()
    return created


def seed_geo(ctx: SeedContext) -> None:
    """Seed currencies from ``currencies.json`` via direct SQL."""
    from src.bootstrap.config import Settings

    rows = _load()
    settings = Settings()  # ty:ignore[missing-argument]
    created = asyncio.run(_run(settings.database_url, rows))

    for row in rows:
        mark = "+" if created > 0 else "~"
        print(f"    {mark} {row['code']:<5} {row['name']}")
    print(f"  --- {created} created, {len(rows) - created} existed")
