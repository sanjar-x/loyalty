# src/bootstrap/taskiq.py
import structlog
from aio_pika.abc import AbstractRobustConnection
from taskiq import AsyncBroker
from taskiq_aio_pika import AioPikaBroker

from src.bootstrap.config import settings

logger = structlog.get_logger(__name__)


class SharedConnectionAioPikaBroker(AioPikaBroker):
    """
    Кастомный TaskIQ брокер, который забирает единое соединение из DI контейнера.
    """

    async def startup(self) -> None:
        await AsyncBroker.startup(self)

        # Если мы в режиме воркера и контейнер еще не проброшен
        if self.is_worker_process and not getattr(
            self, "custom_dependency_context", {}
        ).get("dishka_container"):
            from dishka.integrations.taskiq import setup_dishka

            from src.bootstrap.ioc import create_container

            container = create_container()
            setup_dishka(container=container, broker=self)
            self._worker_dishka_container = container

        container = getattr(self, "custom_dependency_context", {}).get(
            "dishka_container"
        )
        if not container:
            raise RuntimeError(
                "Dishka container must be integrated before broker.startup()"
            )

        connection = await container.get(AbstractRobustConnection)

        self.write_conn = connection
        self.write_channel = await self.write_conn.channel()

        if self.is_worker_process:
            self.read_conn = connection
            self.read_channel = await self.read_conn.channel()

        await self._declare_exchanges()
        await self._declare_queues(self.write_channel)

    async def shutdown(self) -> None:
        await AsyncBroker.shutdown(self)

        for attr in ("write_channel", "read_channel"):
            channel = getattr(self, attr, None)
            if channel and not channel.is_closed:
                await channel.close()
        worker_container = getattr(self, "_worker_dishka_container", None)
        if worker_container:
            await worker_container.close()


broker = SharedConnectionAioPikaBroker(
    url=str(settings.RABBITMQ_URL),
    exchange_name="taskiq_rpc_exchange",
    queue_name="taskiq_background_jobs",
    qos=10,
    declare_exchange=True,
    declare_queue=True,
)
