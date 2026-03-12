from datetime import datetime
from typing import Any, Awaitable, Callable, Protocol

from src.shared.events import IntegrationEvent


class IEventPublisher(Protocol):
    async def publish(
        self, exchange_name: str, routing_key: str, event: IntegrationEvent
    ) -> None:
        """Публикация события в брокер."""
        ...

    async def publish_raw(
        self,
        exchange_name: str,
        routing_key: str,
        payload: dict[str, Any] | str | bytes,
        event_type: str,
        event_id: str,
        occurred_on: datetime | None = None,
    ) -> None:
        """Публикация сырых данных в брокер, минуя строгую типизацию IntegrationEvent."""
        ...


class IEventConsumer(Protocol):
    async def subscribe(
        self,
        queue: str,
        routing_key: str,
        exchange: str,
        handler: Callable[[IntegrationEvent], Awaitable[None]],
    ) -> None:
        """Подписка на очередь с привязкой к обменнику и роутинг-ключу."""
        ...
