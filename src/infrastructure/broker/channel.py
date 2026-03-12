import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional, Tuple

import structlog
from aio_pika.abc import AbstractChannel

from src.infrastructure.broker.connection import ConnectionManager

logger = structlog.get_logger(__name__)


class ChannelPool:
    def __init__(
        self,
        connection_manager: ConnectionManager,
        pool_size: int = 10,
        acquire_timeout: float = 5.0,
    ):
        self._connection_manager = connection_manager
        self._pool_size = pool_size
        self._acquire_timeout = acquire_timeout

        self._channel_pool: asyncio.Queue[Tuple[Optional[AbstractChannel], int]] = (
            asyncio.Queue(maxsize=pool_size)
        )
        self._generation_id: int = 0

        self._init_lock = asyncio.Lock()
        self._initialized = False
        self._is_closing = False

        self._logger = logger.bind(component="rabbitmq_channel_pool")

    async def initialize(self) -> None:
        """Потокобезопасная и параллельная инициализация пула."""
        if self._initialized or self._is_closing:
            return

        async with self._init_lock:
            if self._initialized or self._is_closing:
                return

            self._logger.info(
                "Инициализация пула каналов...", pool_size=self._pool_size
            )
            connection = await self._connection_manager.connect()

            async def _create_channel() -> Optional[AbstractChannel]:
                try:
                    return await connection.channel(publisher_confirms=True)
                except Exception as e:
                    self._logger.error("Ошибка при прогреве канала", error=str(e))
                    return None

            channels = await asyncio.gather(*[
                _create_channel() for _ in range(self._pool_size)
            ])

            for ch in channels:
                self._channel_pool.put_nowait((ch, self._generation_id))

            self._initialized = True
            self._logger.info("Пул каналов успешно инициализирован")

    @asynccontextmanager
    async def acquire(self) -> AsyncGenerator[AbstractChannel, None]:

        channel, generation = await asyncio.wait_for(
            self._channel_pool.get(), timeout=self._acquire_timeout
        )

        yield channel

    async def close(self, timeout: float = 5.0) -> None:
        """Безопасный Shutdown без зависаний."""
        self._is_closing = True
        self._logger.info("Инициализирован graceful shutdown пула каналов...")

        async def _close_channels() -> None:
            while not self._channel_pool.empty():
                try:
                    ch, _ = self._channel_pool.get_nowait()
                    if ch and not getattr(ch, "is_closed", True):
                        await ch.close()
                except asyncio.QueueEmpty:
                    break

        try:
            await asyncio.wait_for(_close_channels(), timeout=timeout)
            self._logger.info("Пул каналов успешно закрыт")
        except asyncio.TimeoutError:
            self._logger.error("Timeout при закрытии пула каналов", timeout=timeout)
