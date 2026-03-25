"""Dishka dependency provider for Redis cache infrastructure.

Manages the Redis connection pool lifecycle and registers the cache
service implementation in the IoC container.
"""

from collections.abc import AsyncIterable

import redis.asyncio as redis
import structlog
from dishka import Provider, Scope, provide
from dishka.dependency_source.composite import CompositeDependencySource
from redis.asyncio.client import Redis
from redis.asyncio.connection import ConnectionPool

from src.bootstrap.config import settings
from src.infrastructure.cache.redis import RedisService
from src.shared.interfaces.cache import ICacheService

logger = structlog.get_logger(__name__)


class CacheProvider(Provider):
    """Dishka provider that supplies Redis client and cache service bindings."""

    @provide(scope=Scope.APP)
    async def redis_client(self) -> AsyncIterable[redis.Redis]:
        """Create and yield a Redis client backed by a connection pool.

        The connection pool is initialized on first use and torn down when
        the application scope is disposed.

        Yields:
            redis.Redis: An async Redis client instance.
        """
        logger.info("Initializing Redis connection pool...", url=settings.redis_url)

        pool: ConnectionPool = redis.ConnectionPool.from_url(
            url=settings.redis_url,
            max_connections=100,
            socket_timeout=5.0,
            socket_connect_timeout=2.0,
            decode_responses=False,
        )
        client: Redis[bytes] = redis.Redis(connection_pool=pool)

        ping: bool = await client.ping()  # type: ignore[misc]
        logger.info("Redis connection established", ping=ping)

        yield client

        logger.info("Closing Redis connection pool...")
        await client.close()
        await pool.disconnect()

    cache_service: CompositeDependencySource = provide(
        source=RedisService, scope=Scope.APP, provides=ICacheService
    )
