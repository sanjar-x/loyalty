# src/infrastructure/cache/provider.py
from collections.abc import AsyncIterable

import redis.asyncio as redis
import structlog
from dishka import Provider, Scope, provide

from src.bootstrap.config import settings
from src.infrastructure.cache.redis import RedisService
from src.shared.interfaces.cache import ICacheService

logger = structlog.get_logger(__name__)


class CacheProvider(Provider):
    @provide(scope=Scope.APP)
    async def redis_client(self) -> AsyncIterable[redis.Redis]:
        logger.info("Инициализация пула соединений Redis...", url=settings.redis_url)

        pool = redis.ConnectionPool.from_url(
            settings.redis_url,
            max_connections=100,
            socket_timeout=5.0,
            socket_connect_timeout=2.0,
            decode_responses=False,
        )
        client = redis.Redis(connection_pool=pool)

        logger.info(
            f"Соединение с Redis успешно установлено (Ping {await client.ping()})"
        )

        yield client

        logger.info("Закрытие пула соединений Redis...")
        await client.close()
        await pool.disconnect()

    cache_service = provide(RedisService, scope=Scope.APP, provides=ICacheService)
