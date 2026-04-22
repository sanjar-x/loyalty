"""Redis-Lists-backed :class:`IEventBufferService` (FIFO buffer)."""

from __future__ import annotations

import redis.asyncio as redis
import structlog
from redis.exceptions import RedisError

from src.shared.interfaces.event_buffer import IEventBufferService

logger = structlog.get_logger(__name__)


class RedisEventBufferService(IEventBufferService):
    def __init__(self, client: redis.Redis) -> None:
        self._client = client

    async def push(self, key: str, *values: str) -> int | None:
        if not values:
            return 0
        try:
            return int(await self._client.rpush(key, *values))
        except RedisError as e:
            logger.warning("RPUSH failed", key=key, error=str(e))
            return None

    async def pop_batch(self, key: str, count: int) -> list[str]:
        if count <= 0:
            return []
        try:
            raw = await self._client.lpop(key, count)
        except RedisError as e:
            logger.warning("LPOP failed", key=key, error=str(e))
            return []
        if raw is None:
            return []
        if isinstance(raw, (bytes, str)):
            raw = [raw]
        return [v.decode("utf-8") if isinstance(v, bytes) else v for v in raw]

    async def length(self, key: str) -> int:
        try:
            return int(await self._client.llen(key))
        except RedisError as e:
            logger.warning("LLEN failed", key=key, error=str(e))
            return 0

    async def set_expire(self, key: str, ttl: int) -> bool:
        try:
            return bool(await self._client.expire(key, ttl))
        except RedisError as e:
            logger.warning("EXPIRE failed", key=key, error=str(e))
            return False
