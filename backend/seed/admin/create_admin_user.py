"""Seed the default admin identity.

DB-only step — does not require the API server to be running. Wraps
``src.modules.identity.management.create_admin.create_admin`` so the
same bootstrap path used operationally is reused here.

Credentials default to the values ``seed/main.py`` later uses to log in
for the API-based steps (``DEFAULT_LOGIN`` / ``DEFAULT_PASSWORD``),
so the end-to-end flow (``roles → admin → geo → brands → ...``) works
without manual intervention.

Requires the ``admin`` role to exist, i.e. run ``roles`` first.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.modules.identity.management.create_admin import create_admin

if TYPE_CHECKING:
    from seed.main import SeedContext


async def _run(
    db_url: str, email: str, password: str, username: str | None
) -> str | None:
    engine = create_async_engine(db_url, echo=False)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    try:
        identity_id = await create_admin(factory, email, password, username)
    finally:
        await engine.dispose()
    return str(identity_id) if identity_id else None


def seed_admin(ctx: SeedContext) -> None:
    """Create the default admin identity (idempotent — skips if email exists)."""
    from src.bootstrap.config import Settings

    settings = Settings()  # type: ignore[call-arg]
    identity_id = asyncio.run(
        _run(settings.database_url, ctx.login, ctx.password, "admin")
    )
    if identity_id:
        print(f"  Admin created: {identity_id} ({ctx.login})")
    else:
        print(f"  Admin already exists ({ctx.login}) — skipped.")
