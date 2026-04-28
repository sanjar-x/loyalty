"""Seed the Yandex Delivery ``provider_accounts`` row for the logistics module.

DB-only step. The logistics registry (``bootstrap_registry`` in
``src/modules/logistics/infrastructure/bootstrap.py``) reads active rows
from ``provider_accounts`` at app startup and constructs the Yandex
Delivery factory + httpx client pool from each row's ``credentials_json``
/ ``config_json``. This step writes that row.

Behaviour:

* ``ENVIRONMENT == "prod"`` → uses ``YANDEX_DELIVERY_OAUTH_TOKEN`` /
  ``YANDEX_DELIVERY_PLATFORM_STATION_ID`` with ``config.test_mode = false``
  (production host ``b2b-authproxy.taxi.yandex.net``).
* Otherwise (``dev`` / ``test``) → uses ``YANDEX_DELIVERY_TEST_OAUTH_TOKEN`` /
  ``YANDEX_DELIVERY_TEST_PLATFORM_STATION_ID`` with ``config.test_mode = true``
  (test host ``b2b.taxi.tst.yandex.net`` — Москва only).

The factory's URL is selected purely by ``test_mode`` — there is no
``YANDEX_*_BASE_URL`` env entry; the constants live in
``providers/yandex_delivery/constants.py``.

Idempotent: keyed on ``provider_code='yandex_delivery'``. Re-running
updates credentials/config on the existing row; the row's ``id``
(deterministic ``uuid5``) is preserved across runs. Skipped (warning, no
error) when the OAuth token for the active environment is empty —
deploys without a Yandex token will simply not register the provider.
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


_PROVIDER_CODE_YANDEX = "yandex_delivery"
_NAMESPACE = uuid.NAMESPACE_DNS


def _resolve_credentials(settings: Any) -> tuple[str, str, bool, str] | None:
    """Pick (oauth_token, platform_station_id, test_mode, name) for the current env.

    Returns ``None`` when the OAuth token for the active environment is
    not configured — seeding is skipped rather than writing a half-empty
    row that would crash ``bootstrap_registry`` at next app start.
    The platform_station_id is optional (empty string is allowed): it
    can be supplied per-request via ``origin.metadata`` and only used
    as a default fallback by the mappers.
    """
    is_prod = str(settings.ENVIRONMENT).lower() == "prod"
    if is_prod:
        token = settings.YANDEX_DELIVERY_OAUTH_TOKEN.get_secret_value()
        station = settings.YANDEX_DELIVERY_PLATFORM_STATION_ID
        return (
            (token, station, False, "Yandex Delivery (production)") if token else None
        )

    token = settings.YANDEX_DELIVERY_TEST_OAUTH_TOKEN.get_secret_value()
    station = settings.YANDEX_DELIVERY_TEST_PLATFORM_STATION_ID
    return (token, station, True, "Yandex Delivery (test)") if token else None


async def _upsert_yandex(
    factory: async_sessionmaker[AsyncSession],
    *,
    oauth_token: str,
    platform_station_id: str,
    test_mode: bool,
    name: str,
) -> str:
    """Upsert a single Yandex Delivery row keyed on ``provider_code``.

    Returns ``"created"`` or ``"updated"`` for the caller to log.
    """
    deterministic_id = uuid.uuid5(
        _NAMESPACE, f"loyality.logistics.provider_account.{_PROVIDER_CODE_YANDEX}"
    )
    credentials_json = {"oauth_token": oauth_token}
    config_json: dict[str, Any] = {"test_mode": test_mode}
    if platform_station_id:
        config_json["platform_station_id"] = platform_station_id

    async with factory() as session:
        existing = await session.execute(
            select(ProviderAccountModel).where(
                ProviderAccountModel.provider_code == _PROVIDER_CODE_YANDEX
            )
        )
        row = existing.scalar_one_or_none()

        if row is None:
            row = ProviderAccountModel(
                id=deterministic_id,
                provider_code=_PROVIDER_CODE_YANDEX,
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

    token, station, test_mode, name = resolved
    engine = create_async_engine(db_url, echo=False)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    try:
        return await _upsert_yandex(
            factory,
            oauth_token=token,
            platform_station_id=station,
            test_mode=test_mode,
            name=name,
        )
    finally:
        await engine.dispose()


def seed_yandex_delivery(ctx: SeedContext) -> None:
    """Upsert the Yandex Delivery ``provider_accounts`` row for the active environment."""
    from src.bootstrap.config import Settings

    del ctx  # DB-only step; SeedContext unused
    settings = Settings()  # type: ignore[call-arg]
    outcome = asyncio.run(_run(settings.database_url, settings))

    if outcome == "skipped":
        env = str(settings.ENVIRONMENT).lower()
        var_name = (
            "YANDEX_DELIVERY_OAUTH_TOKEN"
            if env == "prod"
            else "YANDEX_DELIVERY_TEST_OAUTH_TOKEN"
        )
        print(
            f"  ⚠ Skipped Yandex Delivery seed: {var_name} not set for "
            f"ENVIRONMENT={env!r}. Set the credentials in .env (or via "
            "admin API later) and re-run."
        )
        return

    print(f"  Yandex Delivery provider account {outcome}.")
