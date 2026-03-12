import asyncio
from typing import Any, Optional

import structlog
from aio_pika import connect_robust
from aio_pika.abc import AbstractConnection, AbstractRobustConnection

logger = structlog.get_logger(__name__)


async def setup_rabbitmq_topology(connection: AbstractRobustConnection) -> None:
    """Определяет все необходимые обмены (Exchanges), очереди и DLX."""
    async with connection.channel() as channel:
        # Dead Letter Exchange
        await channel.declare_exchange("dlx", type="direct", durable=True)

        # Обменники приложения (например, для событий каталога)
        await channel.declare_exchange("catalog.events", type="topic", durable=True)

        logger.info("Топология RabbitMQ (Exchanges, DLX) успешно инициализирована")


class ConnectionManager:
    """
    Отвечает исключительно за L4/L7 TCP-соединение с RabbitMQ.
    Зона ответственности: установка соединения, observability (мониторинг состояния),
    graceful shutdown.
    """

    def __init__(
        self,
        amqp_url: str,
        connection_name: str = "fastapi_enterprise_node",
        heartbeat: int = 60,
        reconnect_interval: int = 5,
    ):
        self._amqp_url = amqp_url
        self._connection_name = connection_name
        self._heartbeat = heartbeat
        self._reconnect_interval = reconnect_interval

        self._connection: Optional[AbstractRobustConnection] = None
        self._connection_lock = asyncio.Lock()

        self._logger = logger.bind(
            component="rabbitmq_connection_manager",
            connection_name=self._connection_name,
        )

    async def connect(self) -> AbstractRobustConnection:
        async with self._connection_lock:
            if self._connection is not None and not self._connection.is_closed:
                return self._connection

            self._logger.info("Установка соединения с RabbitMQ...")
            try:
                self._connection = await connect_robust(
                    self._amqp_url,
                    client_properties={"connection_name": self._connection_name},
                    heartbeat=self._heartbeat,
                    timeout=10.0,
                    reconnect_interval=self._reconnect_interval,
                )
                self._connection.close_callbacks.add(self._on_close)

                await setup_rabbitmq_topology(self._connection)

                self._logger.info("Соединение с RabbitMQ успешно установлено")
                return self._connection
            except Exception as e:
                self._logger.error(
                    "Критическая ошибка при первичном подключении", error=str(e)
                )
                raise

    def _on_reconnect(
        self, connection: AbstractRobustConnection, *args: Any, **kwargs: Any
    ) -> None:
        self._logger.warning(
            "Успешное автоматическое переподключение к RabbitMQ (L4/L7)"
        )
        # Пересоздаем Exchange так как aio_pika не делает этого для закрытых каналов
        asyncio.create_task(setup_rabbitmq_topology(connection))

    def _on_close(
        self, sender: Optional[AbstractConnection], exc: Optional[BaseException]
    ) -> None:
        if exc:
            self._logger.error(
                "Соединение с RabbitMQ неожиданно разорвано", error=str(exc)
            )
        else:
            self._logger.info("TCP соединение с RabbitMQ штатно закрыто")

    async def close(self, timeout: float = 5.0) -> None:
        async with self._connection_lock:
            if self._connection is None or self._connection.is_closed:
                return

            self._logger.info(
                "Инициализирован graceful shutdown соединения RabbitMQ..."
            )
            try:
                await asyncio.wait_for(self._connection.close(), timeout=timeout)
                self._logger.info("Соединение с RabbitMQ успешно закрыто")
            except asyncio.TimeoutError:
                self._logger.error(
                    "Timeout при закрытии соединения RabbitMQ", timeout=timeout
                )
            except Exception as e:
                self._logger.error("Ошибка при закрытии соединения", error=str(e))
            finally:
                self._connection = None
