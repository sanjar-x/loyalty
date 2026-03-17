# src/infrastructure/cache/redis.py
import redis.asyncio as redis
import structlog
from redis.exceptions import RedisError

from src.shared.interfaces.cache import ICacheService

logger = structlog.get_logger("redis")


class RedisService(ICacheService):
    def __init__(self, client: redis.Redis):
        self._client = client

    async def set(self, key: str, value: str, ttl: int = 0) -> None:
        try:
            logger.debug("Redis SET", key=key)
            await self._client.set(key, value, ex=ttl if ttl > 0 else None)
        except RedisError as e:
            logger.warning("Ошибка записи в Redis (SET)", key=key, error=str(e))

    async def get(self, key: str) -> str | None:
        try:
            logger.debug("Redis GET", key=key)
            value = await self._client.get(key)
            return value.decode("utf-8") if value else None
        except RedisError as e:
            logger.warning("Ошибка чтения из Redis (GET)", key=key, error=str(e))
            return None

    async def delete(self, key: str) -> None:
        try:
            logger.debug("Redis DELETE", key=key)
            await self._client.delete(key)
        except RedisError as e:
            logger.warning("Ошибка удаления из Redis (DELETE)", key=key, error=str(e))
