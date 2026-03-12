# src/infrastructure/workers/outbox_relay.py
import asyncio
from datetime import datetime

import structlog
from sqlalchemy import select
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

                # 1. Читаем партию (Batch) событий, нуждающихся в публикации
                stmt = (
                    select(OutboxEvent)
                    .where(OutboxEvent.status == OutboxEventStatus.PENDING)
                    .order_by(OutboxEvent.created_at.asc())
                    .limit(batch_size)
                    .with_for_update(
                        skip_locked=True
                    )  # Блокировка от конкурентных воркеров
                )

                result = await session.execute(stmt)
                events = result.scalars().all()

                if not events:
                    # Если событий нет - ждем
                    await asyncio.sleep(poll_interval)
                    continue

                for event in events:
                    try:
                        # 2. Восстанавливаем IntegrationEvent и публикуем
                        # Мы обходим строгую типизацию IntegrationEvent,
                        # так как мы уже имеем готовый payload
                        class _MockEvent:
                            event_id = event.id
                            event_type = event.event_type
                            occurred_on = event.created_at

                            def model_dump(self, **kwargs):
                                return event.payload

                        await publisher.publish(
                            exchange_name=event.exchange,
                            routing_key=event.routing_key,
                            event=_MockEvent(),
                        )

                        # 3. Обновляем статус в случае успеха
                        event.status = OutboxEventStatus.PUBLISHED
                        event.processed_at = datetime.now()
                        logger.debug(
                            "Событие Outbox успешно опубликовано",
                            event_id=str(event.id),
                        )

                    except Exception as e:
                        # 4. Обработка ошибки публикации
                        logger.error(
                            "Ошибка при публикации события Outbox",
                            event_id=str(event.id),
                            error=str(e),
                        )
                        event.status = OutboxEventStatus.FAILED
                        event.error = str(e)
                        event.processed_at = datetime.now()

                # Коммитим партию (освобождаем блокировки FOR UPDATE)
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
