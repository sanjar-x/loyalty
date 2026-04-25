"""TaskIQ scheduled tasks for the logistics module.

* ``tracking_poll_task`` — every 5 minutes; polls BOOKED/CANCEL_PENDING
  shipments and ingests tracking via ``IngestTrackingHandler``.
* ``cleanup_expired_quotes_task`` — hourly; deletes expired
  ``DeliveryQuote`` rows so the table doesn't grow unbounded.
* ``edit_task_poll_task`` — every minute; polls async edit tickets
  for shipments with outstanding ``pending_edit_tasks`` and settles
  the ones that reached a terminal state.
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
from src.modules.logistics.domain.interfaces import (
    IDeliveryQuoteRepository,
    IShipmentRepository,
    IShippingProviderRegistry,
)
from src.modules.logistics.domain.value_objects import (
    EditTaskStatus,
    ShipmentStatus,
)
from src.modules.logistics.infrastructure.models import ShipmentModel
from src.modules.logistics.infrastructure.providers.errors import ProviderHTTPError
from src.shared.interfaces.uow import IUnitOfWork

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
        # The query already filters out NULL provider_shipment_id rows, but
        # the column is typed as ``str | None`` in the ORM model — narrow
        # to ``str`` here to satisfy the annotated return type.
        return [pid for pid in result.scalars().all() if pid is not None]


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
        provider_shipment_ids = await _get_provider_shipment_ids(session_factory, code)

        if not provider_shipment_ids:
            continue

        try:
            results = await poll_provider.poll_tracking_batch(provider_shipment_ids)
        except Exception:
            logger.exception(
                "Tracking poll failed",
                provider=code,
                shipment_count=len(provider_shipment_ids),
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


@broker.task(
    queue="logistics_quotes_cleanup",
    exchange="taskiq_rpc_exchange",
    routing_key="logistics.quotes.cleanup",
    max_retries=0,
    retry_on_error=False,
    timeout=120,
    schedule=[
        {"cron": "0 * * * *", "schedule_id": "cleanup_expired_quotes_hourly"},
    ],
)
@inject
async def cleanup_expired_quotes_task(
    quote_repo: FromDishka[IDeliveryQuoteRepository],
    uow: FromDishka[IUnitOfWork],
) -> dict:
    """Delete delivery quotes whose ``expires_at`` is in the past.

    Quotes are persisted server-side for price-integrity verification,
    but they accumulate quickly because every rate calculation produces
    several. This task runs hourly to keep the ``delivery_quotes`` table
    bounded.
    """
    async with uow:
        deleted = await quote_repo.delete_expired()
        await uow.commit()

    if deleted:
        logger.info("Expired delivery quotes purged", deleted=deleted)
    return {"status": "success", "deleted": deleted}


_TERMINAL_EDIT_STATUSES = (EditTaskStatus.SUCCESS, EditTaskStatus.FAILURE)


@broker.task(
    queue="logistics_edit_task_poll",
    exchange="taskiq_rpc_exchange",
    routing_key="logistics.edit_task.poll",
    max_retries=0,
    retry_on_error=False,
    timeout=120,
    schedule=[
        {"cron": "* * * * *", "schedule_id": "edit_task_poll_every_min"},
    ],
)
@inject
async def edit_task_poll_task(
    shipment_repo: FromDishka[IShipmentRepository],
    registry: FromDishka[IShippingProviderRegistry],
    uow: FromDishka[IUnitOfWork],
) -> dict:
    """Poll outstanding async edit tickets and settle terminal ones.

    Yandex's ``request/edit/status`` endpoint returns one of
    ``pending`` / ``execution`` / ``success`` / ``failure``. Only the
    last two are terminal; we drop the corresponding
    :class:`PendingEditTask` from the shipment and emit
    :class:`ShipmentEditTaskCompletedEvent` /
    :class:`ShipmentEditTaskFailedEvent` accordingly.

    Each shipment is settled in its own UoW commit so a transient
    provider failure on one shipment does not block siblings.
    """
    shipments = await shipment_repo.list_with_pending_edit_tasks(limit=100)
    if not shipments:
        return {"status": "skipped", "reason": "no_pending_edit_tasks"}

    settled = 0
    polled = 0

    for shipment in shipments:
        try:
            edit_provider = registry.get_edit_provider(shipment.provider_code)
        except Exception:
            logger.exception(
                "No edit provider registered for shipment",
                shipment_id=str(shipment.id),
                provider_code=shipment.provider_code,
            )
            continue

        terminals: list[tuple[str, EditTaskStatus]] = []
        for pending in shipment.pending_edit_tasks:
            polled += 1
            try:
                status = await edit_provider.get_edit_status(pending.task_id)
            except ProviderHTTPError:
                logger.exception(
                    "edit/status poll failed",
                    shipment_id=str(shipment.id),
                    task_id=pending.task_id,
                )
                continue
            if status in _TERMINAL_EDIT_STATUSES:
                terminals.append((pending.task_id, status))

        if not terminals:
            continue

        try:
            async with uow:
                fresh = await shipment_repo.get_by_id(shipment.id)
                if fresh is None:
                    continue
                for task_id, terminal in terminals:
                    fresh.settle_edit_task(task_id, terminal)
                await shipment_repo.update(fresh)
                uow.register_aggregate(fresh)
                await uow.commit()
            settled += len(terminals)
        except Exception:
            logger.exception(
                "Failed to persist edit-task settlement",
                shipment_id=str(shipment.id),
                terminal_count=len(terminals),
            )

    logger.info(
        "Edit task poll completed",
        shipments_with_pending=len(shipments),
        tasks_polled=polled,
        tasks_settled=settled,
    )
    return {
        "status": "success",
        "shipments_with_pending": len(shipments),
        "tasks_polled": polled,
        "tasks_settled": settled,
    }
