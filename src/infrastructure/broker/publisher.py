import orjson
import structlog
from aio_pika import DeliveryMode, Message
from aio_pika.abc import AbstractChannel

from src.shared.events import IntegrationEvent
from src.shared.interfaces.broker import IEventPublisher

logger = structlog.get_logger(__name__)


class RabbitMQPublisher(IEventPublisher):
    """
    Enterprise реализация IEventPublisher для RabbitMQ.
    Ожидает, что channel уже сконфигурирован (publisher_confirms=True)
    и внедрен через DI-контейнер (Scope.REQUEST).
    """

    def __init__(self, channel: AbstractChannel):
        self._channel = channel
        self._logger = logger.bind(component="rabbitmq_publisher")

    async def publish(
        self, exchange_name: str, routing_key: str, event: IntegrationEvent
    ) -> None:
        """
        Публикация Integration Event в RabbitMQ с гарантией доставки (Confirms).
        """
        try:
            # 1. Быстрая сериализация payload
            message_body = orjson.dumps(event.model_dump(mode="json"))

            # 2. Формирование AMQP сообщения с полным набором метаданных для DDD/EDA
            message = Message(
                body=message_body,
                message_id=str(event.event_id),
                type=event.event_type,
                content_type="application/json",
                delivery_mode=DeliveryMode.PERSISTENT,
                timestamp=event.occurred_on,
                app_id="fastapi",  # Идентификатор источника
                headers={
                    "event_type": event.event_type,
                    "module_source": event.event_type.split(".")[
                        0
                    ],  # Например: "catalog" из "catalog.category_created"
                    # Здесь в будущем можно добавить "x-correlation-id" или "x-trace-id" для OpenTelemetry
                },
            )

            # 3. Получаем ссылку на обменник (БЕЗ declare!).
            # Ожидается, что инфраструктура/топология поднята заранее.
            exchange = await self._channel.get_exchange(exchange_name)

            # 4. Отправляем сообщение.
            # Так как канал настроен с publisher_confirms=True, этот await
            # "отвиснет" только тогда, когда брокер вернет ACK (записал на диск).
            await exchange.publish(message, routing_key=routing_key)

            self._logger.debug(
                "Integration Event успешно опубликован в RabbitMQ",
                event_id=str(event.event_id),
                event_type=event.event_type,
                exchange=exchange_name,
                routing_key=routing_key,
            )

        except Exception as e:
            self._logger.error(
                "Сбой при публикации Integration Event в RabbitMQ",
                event_id=str(event.event_id),
                event_type=event.event_type,
                error=str(e),
            )
            raise
