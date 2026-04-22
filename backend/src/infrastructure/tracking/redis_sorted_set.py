"""Redis-backed implementation of :class:`ISortedSetService`."""

from __future__ import annotations

import redis.asyncio as redis
import structlog
from redis.exceptions import RedisError

from src.shared.interfaces.sorted_set import ISortedSetService

logger = structlog.get_logger(__name__)


class RedisSortedSetService(ISortedSetService):
    def __init__(self, client: redis.Redis) -> None:
        self._client = client

    @staticmethod
    def _decode(value: bytes | str) -> str:
        return value.decode("utf-8") if isinstance(value, bytes) else value

    async def zincrby(
        self, key: str, increment: float, member: str
    ) -> float | None:
        try:
            return float(await self._client.zincrby(key, increment, member))
        except RedisError as e:
            logger.warning("ZINCRBY failed", key=key, member=member, error=str(e))
            return None

    async def zadd(
        self, key: str, mapping: dict[str, float], *, nx: bool = False
    ) -> int | None:
        if not mapping:
            return 0
        try:
            return int(await self._client.zadd(key, mapping, nx=nx))
        except RedisError as e:
            logger.warning("ZADD failed", key=key, error=str(e))
            return None

    async def zrevrange(
        self, key: str, start: int, stop: int, *, withscores: bool = False
    ) -> list[tuple[str, float]] | list[str] | None:
        try:
            raw = await self._client.zrevrange(
                key, start, stop, withscores=withscores
            )
        except RedisError as e:
            logger.warning("ZREVRANGE failed", key=key, error=str(e))
            return None
        if withscores:
            return [(self._decode(m), float(s)) for m, s in raw]
        return [self._decode(m) for m in raw]

    async def zscore(self, key: str, member: str) -> float | None:
        try:
            raw = await self._client.zscore(key, member)
        except RedisError as e:
            logger.warning("ZSCORE failed", key=key, member=member, error=str(e))
            return None
        return float(raw) if raw is not None else None

    async def zrevrank(self, key: str, member: str) -> int | None:
        try:
            raw = await self._client.zrevrank(key, member)
        except RedisError as e:
            logger.warning("ZREVRANK failed", key=key, error=str(e))
            return None
        return int(raw) if raw is not None else None

    async def zcard(self, key: str) -> int:
        try:
            return int(await self._client.zcard(key))
        except RedisError as e:
            logger.warning("ZCARD failed", key=key, error=str(e))
            return 0

    async def zremrangebyscore(
        self, key: str, min_score: float, max_score: float
    ) -> int:
        try:
            return int(
                await self._client.zremrangebyscore(key, min_score, max_score)
            )
        except RedisError as e:
            logger.warning("ZREMRANGEBYSCORE failed", key=key, error=str(e))
            return 0

    async def zrem(self, key: str, *members: str) -> int:
        if not members:
            return 0
        try:
            return int(await self._client.zrem(key, *members))
        except RedisError as e:
            logger.warning("ZREM failed", key=key, error=str(e))
            return 0

    async def zunionstore(
        self,
        dest: str,
        keys: list[str],
        weights: list[float] | None = None,
    ) -> int:
        try:
            if weights is not None:
                return int(
                    await self._client.zunionstore(dest, keys, weights=weights)
                )
            return int(await self._client.zunionstore(dest, keys))
        except RedisError as e:
            logger.warning("ZUNIONSTORE failed", dest=dest, error=str(e))
            return 0

    async def set_expire(self, key: str, ttl: int) -> bool:
        try:
            return bool(await self._client.expire(key, ttl))
        except RedisError as e:
            logger.warning("EXPIRE failed", key=key, error=str(e))
            return False
