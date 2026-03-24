"""Idempotent sync of seed brands.

Uses ``INSERT ... ON CONFLICT (slug) DO UPDATE`` so it is safe to run
on every deploy.

Usage:
    # Standalone
    python -m src.modules.catalog.management.sync_brands

    # Called from application lifespan
    await sync_brands(session_factory)
"""

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

logger = structlog.get_logger(__name__)

_UPSERT_BRAND = text("""
    INSERT INTO brands (name, slug)
    VALUES (:name, :slug)
    ON CONFLICT (slug) DO UPDATE SET
        name = EXCLUDED.name
""")

# ---------------------------------------------------------------------------
# Seed data — streetwear / fashion starter set
# ---------------------------------------------------------------------------

BRANDS: list[dict[str, str]] = [
    # ── Sportswear ────────────────────────────────────────────────────────
    {"name": "Nike", "slug": "nike"},
    {"name": "Adidas", "slug": "adidas"},
    {"name": "Puma", "slug": "puma"},
    {"name": "New Balance", "slug": "new-balance"},
    {"name": "Reebok", "slug": "reebok"},
    {"name": "ASICS", "slug": "asics"},
    {"name": "Under Armour", "slug": "under-armour"},
    {"name": "Jordan", "slug": "jordan"},
    # ── Streetwear ────────────────────────────────────────────────────────
    {"name": "Stüssy", "slug": "stussy"},
    {"name": "Carhartt WIP", "slug": "carhartt-wip"},
    {"name": "The North Face", "slug": "the-north-face"},
    {"name": "Supreme", "slug": "supreme"},
    {"name": "Palace", "slug": "palace"},
    {"name": "BAPE", "slug": "bape"},
    {"name": "Off-White", "slug": "off-white"},
    {"name": "Essentials", "slug": "essentials"},
    # ── Casual / Denim ────────────────────────────────────────────────────
    {"name": "Levi's", "slug": "levis"},
    {"name": "Dickies", "slug": "dickies"},
    {"name": "Tommy Hilfiger", "slug": "tommy-hilfiger"},
    {"name": "Calvin Klein", "slug": "calvin-klein"},
    {"name": "Lacoste", "slug": "lacoste"},
    {"name": "Ralph Lauren", "slug": "ralph-lauren"},
    {"name": "Hugo Boss", "slug": "hugo-boss"},
    # ── Luxury / Designer ─────────────────────────────────────────────────
    {"name": "Gucci", "slug": "gucci"},
    {"name": "Balenciaga", "slug": "balenciaga"},
    {"name": "Versace", "slug": "versace"},
    # ── Outdoor ───────────────────────────────────────────────────────────
    {"name": "Columbia", "slug": "columbia"},
    {"name": "Patagonia", "slug": "patagonia"},
    {"name": "Arc'teryx", "slug": "arcteryx"},
    # ── Footwear-focused ──────────────────────────────────────────────────
    {"name": "Converse", "slug": "converse"},
    {"name": "Vans", "slug": "vans"},
    {"name": "Dr. Martens", "slug": "dr-martens"},
    {"name": "Timberland", "slug": "timberland"},
    {"name": "Crocs", "slug": "crocs"},
]


async def sync_brands(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Upsert all seed brands. Idempotent — safe to run on every deploy."""
    async with session_factory() as session, session.begin():
        for brand in BRANDS:
            await session.execute(_UPSERT_BRAND, brand)

    logger.info("brands.synced", count=len(BRANDS))


# ---------------------------------------------------------------------------
# Standalone: python -m src.modules.catalog.management.sync_brands
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import asyncio

    from sqlalchemy.ext.asyncio import AsyncSession

    from src.bootstrap.container import create_container
    from src.bootstrap.logger import setup_logging

    setup_logging()

    async def main() -> None:
        container = create_container()
        async with container() as app_scope:
            factory = await app_scope.get(async_sessionmaker[AsyncSession])
            await sync_brands(factory)
        await container.close()

    asyncio.run(main())
