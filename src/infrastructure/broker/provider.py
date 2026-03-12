# src/infrastructure/broker/provider.py
from typing import AsyncIterable

from aio_pika.abc import AbstractChannel
from aio_pika.pool import Pool
from dishka import Provider, Scope, provide

from src.bootstrap.config import Settings
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
        await manager.connect()
        yield manager
        await manager.close()

    @provide(scope=Scope.APP)
    async def get_channel_pool(
        self, connection_manager: ConnectionManager
    ) -> AsyncIterable[Pool[AbstractChannel]]:
        async def get_channel() -> AbstractChannel:
            connection = await connection_manager.connect()
            return await connection.channel(publisher_confirms=True)

        pool = Pool(get_channel, max_size=10)
        yield pool
        await pool.close()

    @provide(scope=Scope.REQUEST)
    def get_rabbitmq_publisher(self, pool: Pool[AbstractChannel]) -> RabbitMQPublisher:
        return RabbitMQPublisher(channel_pool=pool)

    event_publisher = provide(
        OutboxEventPublisher, scope=Scope.REQUEST, provides=IEventPublisher
    )
