from typing import Awaitable, Callable, Protocol

from src.shared.events import IntegrationEvent


class IEventPublisher(Protocol):
    async def publish(
        self, exchange_name: str, routing_key: str, event: IntegrationEvent
    ) -> None:
        """Публикация события в брокер."""
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
