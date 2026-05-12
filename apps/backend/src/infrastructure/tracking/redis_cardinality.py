"""Redis HyperLogLog-backed :class:`ICardinalityService`."""

from __future__ import annotations

import redis.asyncio as redis
import structlog
from redis.exceptions import RedisError

from src.shared.interfaces.cardinality import ICardinalityService

logger = structlog.get_logger(__name__)


class RedisCardinalityService(ICardinalityService):
    def __init__(self, client: redis.Redis) -> None:
        self._client = client

    async def add_to_set(self, key: str, *members: str) -> bool:
        if not members:
            return False
        try:
            return bool(await self._client.pfadd(key, *members))
        except RedisError as e:
            logger.warning("PFADD failed", key=key, error=str(e))
            return False

    async def count(self, key: str) -> int:
        try:
            return int(await self._client.pfcount(key))
        except RedisError as e:
            logger.warning("PFCOUNT failed", key=key, error=str(e))
            return 0

    async def merge(self, dest: str, *source_keys: str) -> bool:
        if not source_keys:
            return False
        try:
            await self._client.pfmerge(dest, *source_keys)
            return True
        except RedisError as e:
            logger.warning("PFMERGE failed", dest=dest, error=str(e))
            return False

    async def set_expire(self, key: str, ttl: int) -> bool:
        try:
            return bool(await self._client.expire(key, ttl))
        except RedisError as e:
            logger.warning("EXPIRE failed", key=key, error=str(e))
            return False
