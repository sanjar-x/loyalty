"""Idempotent sync of marketplace suppliers.

Uses ``INSERT ... ON CONFLICT (id) DO UPDATE`` so it is safe to run
on every deploy.  Seed data comes from ``domain.constants``.

Usage:
    # Standalone
    python -m src.modules.supplier.management.sync_suppliers

    # Called from application lifespan
    await sync_suppliers(session_factory)
"""

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.modules.supplier.domain.constants import SEED_SUPPLIERS

logger = structlog.get_logger(__name__)

_UPSERT_SUPPLIER = text("""
    INSERT INTO suppliers (id, name, type, region, is_active, version)
    VALUES (:id, :name, :type, :region, true, 1)
    ON CONFLICT (id) DO UPDATE SET
        name   = EXCLUDED.name,
        region = EXCLUDED.region
""")


async def sync_suppliers(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Upsert all marketplace suppliers. Idempotent — safe to run on every deploy."""
    async with session_factory() as session, session.begin():
        for supplier in SEED_SUPPLIERS:
            await session.execute(
                _UPSERT_SUPPLIER,
                {
                    "id": str(supplier["id"]),
                    "name": supplier["name"],
                    "type": supplier["type"].name,
                    "region": supplier["region"],
                },
            )

    logger.info("suppliers.synced", count=len(SEED_SUPPLIERS))


# ---------------------------------------------------------------------------
# Standalone: python -m src.modules.supplier.management.sync_suppliers
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
            await sync_suppliers(factory)
        await container.close()

    asyncio.run(main())
