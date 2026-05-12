"""
Read-side Redis queries for activity analytics.

Implements :class:`IActivityQueryService` — all methods degrade gracefully:
when Redis is unreachable (or keys are missing) they return an empty list
and log a warning.  Analytics endpoints therefore remain responsive even
during a Redis outage.

Score semantics
---------------

Scores are raw ZSCORE values as maintained by
:class:`RedisActivityTracker`, i.e. view counts within the TTL window.
The consumer may interpret them as relative popularity; absolute values
are not stable across TTL rollover.
"""

from __future__ import annotations

import uuid

import redis.asyncio as redis

from src.modules.activity.infrastructure.redis_tracker import (
    TRENDING_WEEKLY_KEY,
    search_popular_key,
    search_zero_results_key,
    trending_category_key,
    trending_daily_key,
)
from src.shared.interfaces.activity import RankedEntity
from src.shared.interfaces.logger import ILogger


class RedisActivityQueryService:
    """Concrete :class:`IActivityQueryService` backed by Redis ZSETs."""

    def __init__(self, client: redis.Redis, logger: ILogger) -> None:
        self._client = client
        self._logger = logger.bind(service="RedisActivityQueryService")

    async def get_trending_products(
        self,
        *,
        limit: int = 20,
        window: str = "weekly",
        category_id: uuid.UUID | None = None,
    ) -> list[RankedEntity]:
        if category_id is not None:
            key = trending_category_key(category_id)
        elif window == "daily":
            key = trending_daily_key()
        else:
            key = TRENDING_WEEKLY_KEY
        return await self._zrange_desc(key, limit)

    async def get_popular_search_queries(
        self, *, limit: int = 20
    ) -> list[RankedEntity]:
        return await self._zrange_desc(search_popular_key(), limit)

    async def get_zero_result_queries(self, *, limit: int = 20) -> list[RankedEntity]:
        return await self._zrange_desc(search_zero_results_key(), limit)

    async def _zrange_desc(self, key: str, limit: int) -> list[RankedEntity]:
        """Return the top ``limit`` members sorted by score descending.

        Returns an empty list on Redis failure — callers rely on this
        method as a non-critical best-effort read.
        """
        safe_limit = max(1, min(int(limit), 500))
        try:
            raw = await self._client.zrevrange(key, 0, safe_limit - 1, withscores=True)
        except Exception as exc:  # pragma: no cover - defensive
            self._logger.warning(
                "activity.query.redis_failure",
                key=key,
                error=str(exc),
            )
            return []

        result: list[RankedEntity] = []
        for member, score in raw:
            member_str = (
                member.decode("utf-8") if isinstance(member, bytes) else str(member)
            )
            try:
                score_f = float(score)
            except TypeError, ValueError:
                continue
            result.append(RankedEntity(entity_id=member_str, score=score_f))
        return result
