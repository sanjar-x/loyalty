"""Seed the CDEK ``provider_accounts`` row for the logistics module.

DB-only step. The logistics registry (``bootstrap_registry`` in
``src/modules/logistics/infrastructure/bootstrap.py``) reads active rows
from ``provider_accounts`` at app startup and constructs the CDEK
factory + httpx client pool from each row's ``credentials_json`` /
``config_json``. This step writes that row.

Behaviour:

* ``ENVIRONMENT == "prod"`` → uses ``CDEK_ACCOUNT`` / ``CDEK_SECURE_PASSWORD``
  with ``config.test_mode = false`` (production CDEK API).
* Otherwise (``dev`` / ``test``) → uses ``CDEK_TEST_ACCOUNT`` /
  ``CDEK_TEST_SECURE_PASSWORD`` with ``config.test_mode = true``
  (CDEK ISDK environment ``api.edu.cdek.ru``).

The factory's URL is selected purely by ``test_mode`` — the
``CDEK_BASE_URL`` / ``CDEK_TEST_BASE_URL`` env entries are documentation,
not consumed at runtime.

Idempotent: keyed on ``provider_code='cdek'``. Re-running updates
credentials/config on the existing row; the row's ``id`` (deterministic
``uuid5``) is preserved across runs. Skipped (warning, no error) when
the matching credential pair is empty — production deploys without
CDEK secrets set will simply not register the provider.
"""

from __future__ import annotations

import asyncio
import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.modules.logistics.infrastructure.models import ProviderAccountModel

if TYPE_CHECKING:
    from seed.main import SeedContext


_PROVIDER_CODE_CDEK = "cdek"
_NAMESPACE = uuid.NAMESPACE_DNS


def _resolve_credentials(settings: Any) -> tuple[str, str, bool, str] | None:
    """Pick (account, secure_password, test_mode, name) for the current env.

    Returns ``None`` when the relevant credential pair is not configured —
    seeding is skipped rather than writing a half-empty row that would
    crash ``bootstrap_registry`` at next app start.
    """
    is_prod = str(settings.ENVIRONMENT).lower() == "prod"
    if is_prod:
        account = settings.CDEK_ACCOUNT.get_secret_value()
        password = settings.CDEK_SECURE_PASSWORD.get_secret_value()
        return (
            (account, password, False, "CDEK (production)")
            if account and password
            else None
        )

    account = settings.CDEK_TEST_ACCOUNT.get_secret_value()
    password = settings.CDEK_TEST_SECURE_PASSWORD.get_secret_value()
    return (account, password, True, "CDEK (test)") if account and password else None


async def _upsert_cdek(
    factory: async_sessionmaker[AsyncSession],
    *,
    account: str,
    secure_password: str,
    test_mode: bool,
    name: str,
) -> str:
    """Upsert a single CDEK row keyed on ``provider_code``.

    Returns ``"created"`` or ``"updated"`` for the caller to log.
    """
    deterministic_id = uuid.uuid5(
        _NAMESPACE, f"loyality.logistics.provider_account.{_PROVIDER_CODE_CDEK}"
    )
    credentials_json = {
        "client_id": account,
        "client_secret": secure_password,
    }
    config_json = {
        "test_mode": test_mode,
    }

    async with factory() as session:
        existing = await session.execute(
            select(ProviderAccountModel).where(
                ProviderAccountModel.provider_code == _PROVIDER_CODE_CDEK
            )
        )
        row = existing.scalar_one_or_none()

        if row is None:
            row = ProviderAccountModel(
                id=deterministic_id,
                provider_code=_PROVIDER_CODE_CDEK,
                name=name,
                is_active=True,
                credentials_json=credentials_json,
                config_json=config_json,
            )
            session.add(row)
            outcome = "created"
        else:
            row.name = name
            row.is_active = True
            row.credentials_json = credentials_json
            row.config_json = {**(row.config_json or {}), **config_json}
            outcome = "updated"

        await session.commit()
        return outcome


async def _run(db_url: str, settings: Any) -> str:
    resolved = _resolve_credentials(settings)
    if resolved is None:
        return "skipped"

    account, password, test_mode, name = resolved
    engine = create_async_engine(db_url, echo=False)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    try:
        return await _upsert_cdek(
            factory,
            account=account,
            secure_password=password,
            test_mode=test_mode,
            name=name,
        )
    finally:
        await engine.dispose()


def seed_cdek(ctx: SeedContext) -> None:
    """Upsert the CDEK ``provider_accounts`` row for the active environment."""
    from src.bootstrap.config import Settings

    del ctx  # DB-only step; SeedContext unused
    settings = Settings()  # type: ignore[call-arg]
    outcome = asyncio.run(_run(settings.database_url, settings))

    if outcome == "skipped":
        env = str(settings.ENVIRONMENT).lower()
        var_pair = (
            "CDEK_ACCOUNT / CDEK_SECURE_PASSWORD"
            if env == "prod"
            else "CDEK_TEST_ACCOUNT / CDEK_TEST_SECURE_PASSWORD"
        )
        print(
            f"  ⚠ Skipped CDEK seed: {var_pair} not set for ENVIRONMENT={env!r}. "
            "Set the credentials in .env (or via admin API later) and re-run."
        )
        return

    print(f"  CDEK provider account {outcome}.")
