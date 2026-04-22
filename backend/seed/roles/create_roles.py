"""Seed system roles, permissions, and hierarchy into the database.

DB-only step — does not require the API server to be running. Wraps
``src.modules.identity.management.sync_system_roles`` so that the same
idempotent upsert logic used on application startup is reused here.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.modules.identity.domain.seed import PERMISSIONS, ROLES
from src.modules.identity.management.sync_system_roles import sync_system_roles

if TYPE_CHECKING:
    from seed.main import SeedContext


async def _run(db_url: str) -> None:
    engine = create_async_engine(db_url, echo=False)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    try:
        await sync_system_roles(factory)
    finally:
        await engine.dispose()


def seed_roles(ctx: SeedContext) -> None:
    """Upsert permissions, roles, role-permissions, and role hierarchy."""
    from src.bootstrap.config import Settings

    settings = Settings()  # type: ignore[call-arg]
    asyncio.run(_run(settings.database_url))
    print(f"  Synced {len(PERMISSIONS)} permissions and {len(ROLES)} roles.")
