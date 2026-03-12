# src/infrastructure/broker/provider.py
from typing import AsyncIterable

from aio_pika import connect_robust
from aio_pika.abc import AbstractChannel, AbstractRobustConnection
from aio_pika.pool import Pool
from dishka import Provider, Scope, provide

from src.bootstrap.config import Settings
from src.infrastructure.broker.publisher import RabbitMQPublisher
from src.infrastructure.database.outbox_publisher import OutboxEventPublisher
from src.shared.interfaces.broker import IEventPublisher


class BrokerProvider(Provider):
    @provide(scope=Scope.APP)
    async def get_rabbitmq_connection(
        self, settings: Settings
    ) -> AsyncIterable[AbstractRobustConnection]:
        connection = await connect_robust(
            str(settings.RABBITMQ_URL),
            client_properties={"connection_name": "fastapi_enterprise_node"},
        )
        yield connection
        if not connection.is_closed:
            await connection.close()

    @provide(scope=Scope.APP)
    async def get_channel_pool(
        self, connection: AbstractRobustConnection
    ) -> AsyncIterable[Pool[AbstractChannel]]:
        # The broker.write_conn should be established in lifespan (broker.startup())
        async def get_channel() -> AbstractChannel:
            return await connection.channel(publisher_confirms=True)

        pool = Pool(get_channel, max_size=10)
        yield pool
        pool.close()

    @provide(scope=Scope.REQUEST)
    def get_rabbitmq_publisher(self, pool: Pool[AbstractChannel]) -> RabbitMQPublisher:
        return RabbitMQPublisher(channel_pool=pool)

    event_publisher = provide(
        OutboxEventPublisher, scope=Scope.REQUEST, provides=IEventPublisher
    )
