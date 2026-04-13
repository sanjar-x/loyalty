"""TaskIQ scheduled task: poll tracking updates for active shipments.

Runs every 5 minutes via TaskIQ Beat. For each registered poll provider,
queries BOOKED/CANCEL_PENDING shipments from the DB, calls
``poll_tracking_batch``, and ingests results via ``IngestTrackingHandler``.
"""

import structlog
from dishka.integrations.taskiq import FromDishka, inject
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.bootstrap.broker import broker
from src.modules.logistics.application.commands.ingest_tracking import (
    IngestTrackingCommand,
    IngestTrackingHandler,
)
from src.modules.logistics.domain.interfaces import IShippingProviderRegistry
from src.modules.logistics.domain.value_objects import ShipmentStatus
from src.modules.logistics.infrastructure.models import ShipmentModel

logger = structlog.get_logger(__name__)

_POLLABLE_STATUSES = (
    ShipmentStatus.BOOKED,
    ShipmentStatus.CANCEL_PENDING,
)


async def _get_provider_shipment_ids(
    session_factory: async_sessionmaker[AsyncSession],
    provider_code: str,
) -> list[str]:
    """Load provider_shipment_ids for active shipments of a given provider."""
    async with session_factory() as session:
        stmt = (
            select(ShipmentModel.provider_shipment_id)
            .where(
                ShipmentModel.provider_code == provider_code,
                ShipmentModel.status.in_(_POLLABLE_STATUSES),
                ShipmentModel.provider_shipment_id.is_not(None),
            )
            .limit(200)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())


@broker.task(
    queue="logistics_tracking_poll",
    exchange="taskiq_rpc_exchange",
    routing_key="logistics.tracking.poll",
    max_retries=0,
    retry_on_error=False,
    timeout=240,
    schedule=[
        {"cron": "*/5 * * * *", "schedule_id": "tracking_poll_every_5min"},
    ],
)
@inject
async def tracking_poll_task(
    session_factory: FromDishka[async_sessionmaker[AsyncSession]],
    registry: FromDishka[IShippingProviderRegistry],
    ingest_handler: FromDishka[IngestTrackingHandler],
) -> dict:
    """Poll tracking updates from all registered poll providers."""
    total_updated = 0
    providers_polled = 0

    poll_providers = registry.list_tracking_poll_providers()
    if not poll_providers:
        return {"status": "skipped", "reason": "no_poll_providers"}

    for poll_provider in poll_providers:
        code = poll_provider.provider_code()
        shipment_ids = await _get_provider_shipment_ids(session_factory, code)

        if not shipment_ids:
            continue

        try:
            results = await poll_provider.poll_tracking_batch(shipment_ids)
        except Exception:
            logger.exception(
                "Tracking poll failed",
                provider=code,
                shipment_count=len(shipment_ids),
            )
            continue

        providers_polled += 1

        for provider_shipment_id, events in results.items():
            if not events:
                continue
            try:
                result = await ingest_handler.handle(
                    IngestTrackingCommand(
                        provider_code=code,
                        provider_shipment_id=provider_shipment_id,
                        events=events,
                    )
                )
                total_updated += result.new_events_count
            except Exception:
                logger.exception(
                    "Failed to ingest polling results",
                    provider=code,
                    provider_shipment_id=provider_shipment_id,
                )

    logger.info(
        "Tracking poll completed",
        providers_polled=providers_polled,
        new_events=total_updated,
    )
    return {
        "status": "success",
        "providers_polled": providers_polled,
        "new_events": total_updated,
    }
