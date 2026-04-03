"""Dishka dependency provider for Redis cache infrastructure.

Manages the Redis connection pool lifecycle and registers the cache
service implementation in the IoC container.
"""

from collections.abc import AsyncIterable

import redis.asyncio as redis
import structlog
from dishka import Provider, Scope, provide
from dishka.dependency_source.composite import CompositeDependencySource

from src.bootstrap.config import Settings
from src.infrastructure.cache.redis import RedisService
from src.shared.interfaces.cache import ICacheService

logger = structlog.get_logger(__name__)


class CacheProvider(Provider):
    """Dishka provider that supplies Redis client and cache service bindings."""

    @provide(scope=Scope.APP)
    async def redis_client(self, settings: Settings) -> AsyncIterable[redis.Redis]:
        """Create and yield a Redis client via ``Redis.from_url``.

        The client is torn down when the application scope is disposed.

        Args:
            settings: Application settings containing the Redis URL.

        Yields:
            redis.Redis: An async Redis client instance.
        """
        logger.info("Initializing Redis client...", url=settings.redis_url)

        client = redis.Redis.from_url(settings.redis_url)

        ping: bool = await client.ping()  # ty:ignore[invalid-await]
        logger.info("Redis connection established", ping=ping)

        yield client

        logger.info("Closing Redis client...")
        await client.aclose()

    cache_service: CompositeDependencySource = provide(
        source=RedisService, scope=Scope.APP, provides=ICacheService
    )
