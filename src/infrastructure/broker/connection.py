import structlog
from aio_pika.abc import AbstractRobustConnection

logger = structlog.get_logger(__name__)


async def setup_rabbitmq_topology(connection: AbstractRobustConnection) -> None:
    """Определяет все необходимые обмены (Exchanges), очереди и DLX."""
    async with connection.channel() as channel:
        # Dead Letter Exchange
        await channel.declare_exchange("dlx", type="direct", durable=True)

        # Обменники приложения (например, для событий каталога)
        await channel.declare_exchange("catalog.events", type="topic", durable=True)

        logger.info("Топология RabbitMQ (Exchanges, DLX) успешно инициализирована")
