"""Seed the default admin identity.

DB-only step. Wraps ``src.modules.identity.management.create_admin.create_admin``.
Data source: ``seed/admin/admin.json`` (email, password, username).

Precedence:
  1. ``ctx.login`` / ``ctx.password`` — taken verbatim (they reflect either
     the CLI flags or, by default, the values loaded from admin.json in
     ``seed/main.py``).
  2. ``username`` — always loaded from admin.json (not exposed via CLI).

Requires the ``admin`` role to exist — run ``roles`` first.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.modules.identity.management.create_admin import create_admin

if TYPE_CHECKING:
    from seed.main import SeedContext

_DATA_FILE = Path(__file__).parent / "admin.json"


def _load() -> dict:
    return json.loads(_DATA_FILE.read_text(encoding="utf-8"))


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

    defaults = _load()
    username = defaults.get("username", "admin")

    settings = Settings()  # type: ignore[call-arg]
    identity_id = asyncio.run(
        _run(settings.database_url, ctx.login, ctx.password, username)
    )
    if identity_id:
        print(f"  Admin created: {identity_id} ({ctx.login})")
    else:
        print(f"  Admin already exists ({ctx.login}) — skipped.")
