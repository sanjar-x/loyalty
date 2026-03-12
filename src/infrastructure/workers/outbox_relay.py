# src/infrastructure/workers/outbox_relay.py
import asyncio
from datetime import datetime, timedelta

import structlog
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.bootstrap.ioc import create_container
from src.infrastructure.broker.publisher import RabbitMQPublisher
from src.infrastructure.database.models import OutboxEvent, OutboxEventStatus

logger = structlog.get_logger(__name__)


async def run_outbox_relay(batch_size: int = 50, poll_interval: float = 2.0):
    """
    Фоновый процесс (Relay) для шаблона Transactional Outbox.
    Читает PENDING события из БД и безопасно отправляет в RabbitMQ.
    """
    logger.info("Запуск Outbox Relay Worker", batch_size=batch_size)

    # Инициализация корневого IoC-контейнера (Scope.APP)
    container = create_container()

    try:
        while True:
            # Создаем Scope.REQUEST для получения сессии и канала брокера
            async with container() as request_container:
                session = await request_container.get(AsyncSession)
                publisher = await request_container.get(RabbitMQPublisher)

                # Транзакция 1: SELECT FOR UPDATE SKIP LOCKED и в PROCESSING
                # Берем PENDING события + зависшие PROCESSING события (старше 5 минут)
                five_mins_ago = datetime.now() - timedelta(minutes=5)
                stmt = (
                    select(OutboxEvent)
                    .where(
                        or_(
                            OutboxEvent.status == OutboxEventStatus.PENDING,
                            (
                                (OutboxEvent.status == OutboxEventStatus.PROCESSING)
                                & (OutboxEvent.updated_at < five_mins_ago)
                            ),
                        )
                    )
                    .order_by(OutboxEvent.created_at.asc())
                    .limit(batch_size)
                    .with_for_update(skip_locked=True)
                )

                result = await session.execute(stmt)
                events = result.scalars().all()

                if not events:
                    await asyncio.sleep(poll_interval)
                    continue

                for event in events:
                    event.status = OutboxEventStatus.PROCESSING

                # Коммитим Транзакцию 1: снимаем эксклюзивные локи БД!
                # Строки теперь заблокированы логически (status = PROCESSING)
                await session.commit()

                # I/O Операции (Вне транзакции БД)
                # Формируем батч сырых данных для мультиплексирования через 1 AMQP канал
                events_data = [
                    {
                        "exchange_name": event.exchange,
                        "routing_key": event.routing_key,
                        "payload": event.payload,
                        "event_type": event.event_type,
                        "event_id": str(event.id),
                        "occurred_on": event.created_at,
                    }
                    for event in events
                ]

                results = await publisher.publish_raw_batch(events_data)

                for event, result in zip(events, results):
                    if isinstance(result, Exception):
                        event.status = OutboxEventStatus.FAILED
                        event.error = str(result)
                        logger.error(
                            "Ошибка публикации события",
                            event_id=str(event.id),
                            error=str(result),
                        )
                    else:
                        event.status = OutboxEventStatus.PUBLISHED
                        logger.debug(
                            "Событие успешно опубликовано", event_id=str(event.id)
                        )
                    event.processed_at = datetime.now()

                # Транзакция 2: Сохраняем итоговые статусы (PUBLISHED или FAILED)
                for event in events:
                    session.add(event)
                await session.commit()

            # Небольшая пауза между батчами, если они идут потоком
            await asyncio.sleep(0.1)

    except asyncio.CancelledError:
        logger.info("Получен сигнал на остановку Outbox Relay...")
    except Exception as e:
        logger.error("Критическая ошибка в Outbox Relay", exc_info=e)
    finally:
        logger.info("Закрытие DI контейнера Relay Worker...")
        await container.close()


if __name__ == "__main__":
    try:
        asyncio.run(run_outbox_relay())
    except KeyboardInterrupt:
        pass
