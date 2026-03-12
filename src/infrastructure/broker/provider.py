# src/infrastructure/broker/provider.py
from typing import AsyncIterable

from aio_pika.abc import AbstractChannel
from dishka import Provider, Scope, provide

from src.bootstrap.config import Settings
from src.infrastructure.broker.channel import ChannelPool
from src.infrastructure.broker.connection import ConnectionManager
from src.infrastructure.broker.publisher import RabbitMQPublisher
from src.infrastructure.database.outbox_publisher import OutboxEventPublisher
from src.shared.interfaces.broker import IEventPublisher


class BrokerProvider(Provider):
    @provide(scope=Scope.APP)
    async def get_connection_manager(
        self, settings: Settings
    ) -> AsyncIterable[ConnectionManager]:
        manager = ConnectionManager(amqp_url=settings.RABBITMQ_URL)
        # Connect initially or let the pool do it
        yield manager
        await manager.close()

    @provide(scope=Scope.APP)
    async def get_channel_pool(
        self, connection_manager: ConnectionManager
    ) -> AsyncIterable[ChannelPool]:
        pool = ChannelPool(connection_manager=connection_manager, pool_size=10)
        await pool.initialize()
        yield pool
        await pool.close()

    @provide(scope=Scope.REQUEST)
    async def get_channel(self, pool: ChannelPool) -> AsyncIterable[AbstractChannel]:
        async with pool.acquire() as channel:
            yield channel

    @provide(scope=Scope.REQUEST)
    def get_rabbitmq_publisher(self, channel: AbstractChannel) -> RabbitMQPublisher:
        return RabbitMQPublisher(channel=channel)

    event_publisher = provide(
        OutboxEventPublisher, scope=Scope.REQUEST, provides=IEventPublisher
    )
