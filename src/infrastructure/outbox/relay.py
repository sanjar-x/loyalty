# src/infrastructure/outbox/relay.py
"""
Outbox Relay: читает необработанные события из таблицы outbox_messages
и публикует их в RabbitMQ через TaskIQ.

Паттерн: Polling Publisher с FOR UPDATE SKIP LOCKED для конкурентной
безопасности (несколько Relay-воркеров могут работать параллельно).
"""

from __future__ import annotations

import uuid
from typing import Any

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Реестр обработчиков событий: event_type → async callable(payload)
# Relay вызывает соответствующий handler для публикации в брокер.
# ---------------------------------------------------------------------------
EventHandler = Any  # Callable[[dict], Awaitable[None]]
_EVENT_HANDLERS: dict[str, EventHandler] = {}


def register_event_handler(event_type: str, handler: EventHandler) -> None:
    """Регистрирует обработчик для типа события."""
    _EVENT_HANDLERS[event_type] = handler


# ---------------------------------------------------------------------------
# Core Relay Logic
# ---------------------------------------------------------------------------

# SQL с FOR UPDATE SKIP LOCKED — несколько воркеров не блокируют друг друга
_FETCH_UNPROCESSED_SQL = text(
    text="""
    SELECT id, event_type, payload, correlation_id
    FROM outbox_messages
    WHERE processed_at IS NULL
    ORDER BY created_at ASC
    LIMIT :batch_size
    FOR UPDATE SKIP LOCKED
"""
)

_MARK_PROCESSED_SQL = text(
    text="""
    UPDATE outbox_messages
    SET processed_at = NOW()
    WHERE id = ANY(:ids)
"""
)


async def relay_outbox_batch(
    session_factory: async_sessionmaker[AsyncSession],
    batch_size: int = 100,
) -> int:
    """
    Забирает пачку необработанных событий из Outbox и отправляет в брокер.

    Возвращает количество успешно обработанных событий.
    Если брокер недоступен — транзакция откатывается, блокировка снимается,
    следующий цикл поллинга подхватит эти же события (At-Least-Once).
    """
    processed_ids: list[uuid.UUID] = []

    async with session_factory() as session:
        async with session.begin():
            result = await session.execute(
                _FETCH_UNPROCESSED_SQL,
                {"batch_size": batch_size},
            )
            rows = result.fetchall()

            if not rows:
                return 0

            for row in rows:
                event_id = row.id
                event_type = row.event_type
                payload = row.payload
                correlation_id = getattr(row, "correlation_id", None) or (
                    "relay-" + uuid.uuid4().hex[:12]
                )
                structlog.contextvars.bind_contextvars(
                    correlation_id=correlation_id,
                    event_id=str(event_id),
                    event_type=event_type,
                )

                handler = _EVENT_HANDLERS.get(event_type)
                if handler is None:
                    logger.warning(
                        "Outbox Relay: неизвестный event_type, пропуск",
                        event_type=event_type,
                        event_id=str(event_id),
                    )
                    processed_ids.append(event_id)
                    continue

                try:
                    await handler(payload)
                    processed_ids.append(event_id)
                    logger.debug(
                        "Outbox Relay: событие отправлено в брокер",
                        event_type=event_type,
                        event_id=str(event_id),
                    )
                except Exception:
                    logger.exception(
                        "Outbox Relay: ошибка отправки события, "
                        "транзакция будет откачена",
                        event_type=event_type,
                        event_id=str(event_id),
                    )
                    raise
            if processed_ids:
                await session.execute(
                    _MARK_PROCESSED_SQL,
                    {"ids": processed_ids},
                )

    logger.info(
        "Outbox Relay: батч обработан",
        processed=len(processed_ids),
        total_in_batch=len(rows),
    )
    return len(processed_ids)


# ---------------------------------------------------------------------------
# Pruning: очистка обработанных записей старше N дней
# ---------------------------------------------------------------------------

_PRUNE_SQL = text("""
    DELETE FROM outbox_messages
    WHERE processed_at IS NOT NULL
      AND processed_at < NOW() - INTERVAL '7 days'
""")


async def prune_processed_messages(
    session_factory: async_sessionmaker[AsyncSession],
) -> int:
    """
    Удаляет обработанные Outbox-записи старше 7 дней.
    Предотвращает разрастание таблицы и замедление vacuum в PostgreSQL.
    """
    async with session_factory() as session:
        async with session.begin():
            result = await session.execute(_PRUNE_SQL)
            deleted = result.rowcount

    if deleted:
        logger.info("Outbox Pruning: удалено старых записей", count=deleted)
    return deleted
