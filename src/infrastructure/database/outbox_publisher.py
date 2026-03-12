# src/infrastructure/database/outbox_publisher.py
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models import OutboxEvent
from src.shared.events import IntegrationEvent
from src.shared.interfaces.broker import IEventPublisher

logger = structlog.get_logger(__name__)


class OutboxEventPublisher(IEventPublisher):
    """
    Реализация Transactional Outbox.
    Вместо прямой отправки в брокер, сохраняет событие в БД
    с помощью той же сессии (и транзакции), что и бизнес-сущность.
    """

    def __init__(self, session: AsyncSession):
        self._session = session
        self._logger = logger.bind(component="outbox_publisher")

    async def publish(
        self, exchange_name: str, routing_key: str, event: IntegrationEvent
    ) -> None:
        outbox_event = OutboxEvent(
            event_type=event.event_type,
            exchange=exchange_name,
            routing_key=routing_key,
            payload=event.model_dump(mode="json"),
        )
        self._session.add(outbox_event)
        self._logger.debug(
            "Событие добавлено в Transactional Outbox (БД)",
            event_id=str(event.event_id),
            event_type=event.event_type,
            exchange=exchange_name,
            routing_key=routing_key,
        )

    async def publish_batch(
        self, exchange_name: str, routing_key: str, events: list[IntegrationEvent]
    ) -> None:
        outbox_events = [
            OutboxEvent(
                event_type=event.event_type,
                exchange=exchange_name,
                routing_key=routing_key,
                payload=event.model_dump(mode="json"),
            )
            for event in events
        ]
        self._session.add_all(outbox_events)
        self._logger.debug(
            "Пакет событий добавлен в Transactional Outbox (БД)",
            count=len(events),
            exchange=exchange_name,
            routing_key=routing_key,
        )
