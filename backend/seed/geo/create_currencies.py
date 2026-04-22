"""Seed minimal currency data required by product variants and SKUs.

Uses direct DB connection (no HTTP API for currencies).
Called by seed/main.py as part of the seeding flow.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

if TYPE_CHECKING:
    from seed.main import SeedContext

CURRENCIES = [
    ("RUB", "643", "Russian Ruble", "R", 2),
    ("USD", "840", "US Dollar", "$", 2),
    ("EUR", "978", "Euro", "E", 2),
    ("UZS", "860", "Uzbekistani Som", "S", 2),
]

UPSERT = text(
    "INSERT INTO currencies (code, numeric, name, symbol, decimal_places, is_active) "
    "VALUES (:code, :num, :name, :sym, :dec, true) "
    "ON CONFLICT (code) DO NOTHING"
)


async def _run(db_url: str) -> int:
    engine = create_async_engine(db_url, echo=False)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    created = 0
    async with factory() as s, s.begin():
        for code, num, name, sym, dec in CURRENCIES:
            r = await s.execute(UPSERT, {"code": code, "num": num, "name": name, "sym": sym, "dec": dec})
            if r.rowcount and r.rowcount > 0:
                created += 1
    await engine.dispose()
    return created


def seed_geo(ctx: SeedContext) -> None:
    """Seed currencies via direct SQL (no HTTP API exists for geo data)."""
    from src.bootstrap.config import Settings

    settings = Settings()  # type: ignore[call-arg]
    created = asyncio.run(_run(settings.database_url))

    for code, _, name, _, _ in CURRENCIES:
        mark = "+" if created > 0 else "~"
        print(f"    {mark} {code:<5} {name}")
    print(f"  --- {created} created, {len(CURRENCIES) - created} existed")
