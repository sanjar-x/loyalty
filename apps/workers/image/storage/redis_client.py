"""Redis client singleton — used by the status publisher.

Named ``redis_client`` rather than ``redis`` so the module doesn't
shadow the PyPI ``redis`` package when other files do
``from redis.asyncio import Redis``.
"""

from __future__ import annotations

from redis.asyncio import Redis

from config import settings

redis_client: Redis = Redis.from_url(settings.redis_url)
