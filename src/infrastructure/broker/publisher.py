from datetime import datetime
from typing import Any

import orjson
import structlog
from aio_pika import DeliveryMode, Message
from aio_pika.abc import AbstractChannel
from aio_pika.pool import Pool

from src.shared.events import IntegrationEvent
from src.shared.interfaces.broker import IEventPublisher

logger = structlog.get_logger(__name__)


class RabbitMQPublisher(IEventPublisher):
    """
    Enterprise реализация IEventPublisher для RabbitMQ.
    Ожидает, что channel уже сконфигурирован (publisher_confirms=True)
    и внедрен через DI-контейнер (Scope.REQUEST).
    """

    def __init__(self, channel_pool: Pool[AbstractChannel]):
        self._pool = channel_pool
        self._logger = logger.bind(component="rabbitmq_publisher")

    async def publish(
        self, exchange_name: str, routing_key: str, event: IntegrationEvent
    ) -> None:
        """
        Публикация Integration Event в RabbitMQ с гарантией доставки (Confirms).
        """
        message_body = orjson.dumps(event.model_dump(mode="json"))
        await self.publish_raw(
            exchange_name=exchange_name,
            routing_key=routing_key,
            payload=message_body,
            event_type=event.event_type,
            event_id=str(event.event_id),
            occurred_on=event.occurred_on,
        )

    async def publish_batch(
        self, exchange_name: str, routing_key: str, events: list[IntegrationEvent]
    ) -> None:
        import asyncio

        tasks = [self.publish(exchange_name, routing_key, event) for event in events]
        await asyncio.gather(*tasks)

    async def publish_raw(
        self,
        exchange_name: str,
        routing_key: str,
        payload: dict[str, Any] | str | bytes,
        event_type: str,
        event_id: str,
        occurred_on: datetime | None = None,
    ) -> None:
        """
        Публикация сырых данных напрямую в RabbitMQ.
        """
        try:
            if isinstance(payload, dict):
                message_body = orjson.dumps(payload)
            elif isinstance(payload, str):
                message_body = payload.encode("utf-8")
            else:
                message_body = payload

            message = Message(
                body=message_body,
                message_id=event_id,
                type=event_type,
                content_type="application/json",
                delivery_mode=DeliveryMode.PERSISTENT,
                timestamp=occurred_on,
                app_id="fastapi",
                headers={
                    "event_type": event_type,
                    "module_source": event_type.split(".")[0],
                },
            )

            async with self._pool.acquire() as channel:
                exchange = await channel.get_exchange(exchange_name, ensure=False)
                await exchange.publish(message, routing_key=routing_key)

            self._logger.debug(
                "Integration Event успешно опубликован в RabbitMQ",
                event_id=event_id,
                event_type=event_type,
                exchange=exchange_name,
                routing_key=routing_key,
            )

        except Exception as e:
            self._logger.error(
                "Сбой при публикации Integration Event в RabbitMQ",
                event_id=event_id,
                event_type=event_type,
                error=str(e),
            )
            raise

    async def publish_raw_batch(
        self, events_data: list[dict[str, Any]]
    ) -> list[Exception | None]:
        """
        Массовая конкурентная публикация сырых данных через ОДИН AMQP-канал.
        Снижает Lock Contention в пуле каналов.
        """
        import asyncio

        async with self._pool.acquire() as channel:
            tasks = []

            async def _publish(ev_data: dict[str, Any]) -> None:
                try:
                    payload = ev_data["payload"]
                    if isinstance(payload, dict):
                        body = orjson.dumps(payload)
                    elif isinstance(payload, str):
                        body = payload.encode("utf-8")
                    else:
                        body = payload

                    message = Message(
                        body=body,
                        message_id=ev_data["event_id"],
                        type=ev_data["event_type"],
                        content_type="application/json",
                        delivery_mode=DeliveryMode.PERSISTENT,
                        timestamp=ev_data["occurred_on"],
                        app_id="fastapi",
                        headers={
                            "event_type": ev_data["event_type"],
                            "module_source": ev_data["event_type"].split(".")[0],
                        },
                    )
                    # ensure=False убирает лишние сетевые I/O запросы
                    exchange = await channel.get_exchange(
                        ev_data["exchange_name"], ensure=False
                    )
                    await exchange.publish(message, routing_key=ev_data["routing_key"])
                except Exception as e:
                    self._logger.error(
                        "Сбой при публикации сырого батча в RabbitMQ",
                        event_id=ev_data.get("event_id"),
                        error=str(e),
                    )
                    raise e

            for ev in events_data:
                tasks.append(_publish(ev))

            results = await asyncio.gather(*tasks, return_exceptions=True)
            return [res if isinstance(res, Exception) else None for res in results]
