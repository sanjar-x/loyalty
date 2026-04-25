"""
Bootstrap logistics provider registry from ProviderAccountModel records.

Loads active provider accounts from the database at startup (APP scope),
creates capability providers via the appropriate factory, and registers
them into the ShippingProviderRegistry.
"""

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.modules.logistics.domain.interfaces import IProviderFactory
from src.modules.logistics.domain.value_objects import (
    PROVIDER_CDEK,
    PROVIDER_YANDEX_DELIVERY,
)
from src.modules.logistics.infrastructure.models import ProviderAccountModel
from src.modules.logistics.infrastructure.providers.cdek.factory import (
    CdekProviderFactory,
)
from src.modules.logistics.infrastructure.providers.yandex_delivery.factory import (
    YandexDeliveryProviderFactory,
)
from src.modules.logistics.infrastructure.services.registry import (
    ShippingProviderRegistry,
)

logger = logging.getLogger(__name__)

_FACTORY_MAP: dict[str, type[IProviderFactory]] = {
    PROVIDER_CDEK: CdekProviderFactory,
    PROVIDER_YANDEX_DELIVERY: YandexDeliveryProviderFactory,
}


async def bootstrap_registry(
    session_factory: async_sessionmaker[AsyncSession],
) -> ShippingProviderRegistry:
    """Create and populate a ShippingProviderRegistry from DB records.

    Opens a short-lived session, loads all active ProviderAccountModel rows,
    and for each one creates and registers all capability providers via
    the matching factory.
    """
    registry = ShippingProviderRegistry()

    async with session_factory() as session:
        stmt = select(ProviderAccountModel).where(
            ProviderAccountModel.is_active.is_(True)
        )
        result = await session.execute(stmt)
        accounts = result.scalars().all()

    if not accounts:
        logger.warning("No active provider accounts found — registry is empty")
        return registry

    factories: dict[str, IProviderFactory] = {}

    for account in accounts:
        code = account.provider_code
        credentials: dict[str, Any] = account.credentials_json or {}
        config: dict[str, Any] = account.config_json or {}

        if code in factories:
            logger.warning(
                "Duplicate active account for provider '%s' (id=%s) — skipping",
                code,
                account.id,
            )
            continue

        factory_cls = _FACTORY_MAP.get(code)
        if factory_cls is None:
            logger.warning(
                "No factory registered for provider '%s' (account id=%s) — skipping",
                code,
                account.id,
            )
            continue

        factory = factory_cls()

        try:
            _register_capabilities(registry, factory, credentials, config)
        except Exception:
            # One bad ProviderAccount must not take down the whole App.
            # ``credentials_json`` may be malformed (missing client_id /
            # oauth_token), or the factory may raise on construction —
            # either way, log and skip so the other providers come up.
            logger.exception(
                "Failed to register provider '%s' (account '%s', id=%s) — skipping",
                code,
                account.name,
                account.id,
            )
            continue

        factories[code] = factory
        logger.info(
            "Registered provider '%s' (account '%s', id=%s)",
            code,
            account.name,
            account.id,
        )

    # Hold factory references on the registry's lifecycle so cached
    # ``httpx.AsyncClient`` instances are closed at app shutdown rather
    # than leaking until process exit.
    for factory in factories.values():
        registry.register_close_callback(factory.close)

    return registry


def _register_capabilities(
    registry: ShippingProviderRegistry,
    factory: IProviderFactory,
    credentials: dict[str, Any],
    config: dict[str, Any],
) -> None:
    """Call each factory method and register non-None results."""
    rate = factory.create_rate_provider(credentials, config)
    if rate is not None:
        registry.register_rate_provider(rate)

    booking = factory.create_booking_provider(credentials, config)
    if booking is not None:
        registry.register_booking_provider(booking)

    tracking = factory.create_tracking_provider(credentials, config)
    if tracking is not None:
        registry.register_tracking_provider(tracking)

    poll = factory.create_tracking_poll_provider(credentials, config)
    if poll is not None:
        registry.register_tracking_poll_provider(poll)

    pickup = factory.create_pickup_point_provider(credentials, config)
    if pickup is not None:
        registry.register_pickup_point_provider(pickup)

    document = factory.create_document_provider(credentials, config)
    if document is not None:
        registry.register_document_provider(document)

    webhook = factory.create_webhook_adapter(credentials, config)
    if webhook is not None:
        registry.register_webhook_adapter(webhook)

    intake = factory.create_intake_provider(credentials, config)
    if intake is not None:
        registry.register_intake_provider(intake)

    schedule = factory.create_delivery_schedule_provider(credentials, config)
    if schedule is not None:
        registry.register_delivery_schedule_provider(schedule)

    returns = factory.create_return_provider(credentials, config)
    if returns is not None:
        registry.register_return_provider(returns)

    edit = factory.create_edit_provider(credentials, config)
    if edit is not None:
        registry.register_edit_provider(edit)
