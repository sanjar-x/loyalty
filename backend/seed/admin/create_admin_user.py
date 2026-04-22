"""Seed the default admin identity.

DB-only step. Wraps ``src.modules.identity.management.create_admin.create_admin``.
Data source: ``seed/admin/admin.json`` (email, password, username).

The JSON credentials MUST match ``seed/main.py`` ``SeedContext.login`` /
``password`` so that subsequent API steps can log in with them. When the
caller overrides ``--login`` / ``--password`` on the CLI, those values
win — the JSON acts as a default only.

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
    """Create the default admin identity (idempotent — skips if email exists).

    Precedence: CLI overrides (``ctx.login``/``ctx.password``) take priority
    over ``admin.json`` defaults, so operators can bootstrap a non-default
    admin without editing the JSON.
    """
    from seed.main import DEFAULT_LOGIN, DEFAULT_PASSWORD
    from src.bootstrap.config import Settings

    defaults = _load()
    email = ctx.login if ctx.login != DEFAULT_LOGIN else defaults["email"]
    password = ctx.password if ctx.password != DEFAULT_PASSWORD else defaults["password"]
    username = defaults.get("username", "admin")

    settings = Settings()  # type: ignore[call-arg]
    identity_id = asyncio.run(_run(settings.database_url, email, password, username))
    if identity_id:
        print(f"  Admin created: {identity_id} ({email})")
    else:
        print(f"  Admin already exists ({email}) — skipped.")
