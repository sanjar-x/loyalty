# src/infrastructure/broker/provider.py
from typing import AsyncIterable

from aio_pika.abc import AbstractChannel
from aio_pika.pool import Pool
from dishka import Provider, Scope, provide

from src.bootstrap.taskiq import broker as taskiq_broker
from src.infrastructure.broker.publisher import RabbitMQPublisher
from src.infrastructure.database.outbox_publisher import OutboxEventPublisher
from src.shared.interfaces.broker import IEventPublisher


class BrokerProvider(Provider):
    @provide(scope=Scope.APP)
    async def get_channel_pool(self) -> AsyncIterable[Pool[AbstractChannel]]:
        # The broker.write_conn should be established in lifespan (broker.startup())
        async def get_channel() -> AbstractChannel:
            connection = taskiq_broker.write_conn
            if not connection or connection.is_closed:
                raise RuntimeError(
                    "TaskIQ Broker connection is not established or closed."
                )
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
