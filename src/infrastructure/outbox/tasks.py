# src/infrastructure/outbox/tasks.py
"""
TaskIQ-задачи для Outbox Relay и Pruning.

Relay: периодический поллинг outbox_messages (каждые 2 секунды).
Pruning: ежесуточная очистка обработанных записей старше 7 дней.
"""

import uuid

import structlog
from dishka.integrations.taskiq import FromDishka, inject
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.bootstrap.broker import broker
from src.infrastructure.outbox.relay import (
    prune_processed_messages,
    register_event_handler,
    relay_outbox_batch,
)

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Регистрация обработчиков событий (event_type → TaskIQ dispatch)
# ---------------------------------------------------------------------------


async def _handle_brand_logo_confirmed(payload: dict) -> None:
    """Отправляет задачу обработки логотипа бренда в TaskIQ."""
    from src.modules.catalog.application.tasks import process_brand_logo_task

    brand_id = uuid.UUID(payload["brand_id"])
    await process_brand_logo_task.kiq(brand_id=brand_id)  # type: ignore[call-overload]


# Регистрируем маппинг: event_type → handler
register_event_handler("BrandLogoConfirmedEvent", _handle_brand_logo_confirmed)


# ---------------------------------------------------------------------------
# TaskIQ: Outbox Relay (периодический поллинг)
# ---------------------------------------------------------------------------


@broker.task(
    queue="outbox_relay",
    exchange="taskiq_rpc_exchange",
    routing_key="infrastructure.outbox.relay",
    max_retries=0,
    retry_on_error=False,
)
@inject
async def outbox_relay_task(
    session_factory: FromDishka[async_sessionmaker[AsyncSession]],
) -> dict:
    """
    Периодическая задача: забирает батч из Outbox и публикует в брокер.
    Запускается через TaskIQ Beat каждые 2 секунды.
    """
    try:
        processed = await relay_outbox_batch(
            session_factory=session_factory,
            batch_size=100,
        )
        return {"status": "success", "processed": processed}
    except Exception:
        logger.exception("Outbox Relay: критическая ошибка в цикле поллинга")
        return {"status": "error", "processed": 0}


# ---------------------------------------------------------------------------
# TaskIQ: Outbox Pruning (ежесуточная очистка)
# ---------------------------------------------------------------------------


@broker.task(
    queue="outbox_pruning",
    exchange="taskiq_rpc_exchange",
    routing_key="infrastructure.outbox.pruning",
    max_retries=1,
    retry_on_error=True,
)
@inject
async def outbox_pruning_task(
    session_factory: FromDishka[async_sessionmaker[AsyncSession]],
) -> dict:
    """
    Ежесуточная задача: удаляет обработанные Outbox-записи старше 7 дней.
    Запускается через TaskIQ Beat раз в сутки (ночью).
    """
    deleted = await prune_processed_messages(session_factory=session_factory)
    return {"status": "success", "deleted": deleted}
