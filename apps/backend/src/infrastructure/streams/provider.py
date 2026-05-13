"""Dishka dependency provider for the channel-stream infrastructure.

Composes a :class:`RedisStreamChannel` on top of the workspace-wide
Redis client owned by :class:`CacheProvider`. There is exactly one
binding (``IChannelStream``) at ``APP`` scope — the implementation is
stateless aside from the Redis connection it borrows, so a single
shared instance is correct and avoids per-request churn.
"""

from __future__ import annotations

from dishka import Provider, Scope, provide
from redis.asyncio import Redis

from src.infrastructure.streams.redis_streams import RedisStreamChannel
from src.shared.interfaces.channel_stream import IChannelStream


class StreamsProvider(Provider):
    """Dishka provider that supplies the :class:`IChannelStream` binding."""

    @provide(scope=Scope.APP)
    def channel_stream(self, redis: Redis) -> IChannelStream:
        """Build the singleton :class:`RedisStreamChannel`.

        The Redis client itself is owned by :class:`CacheProvider`
        (single connection pool reused across cache + streams + future
        Redis consumers); this provider only wires the binding.
        """
        return RedisStreamChannel(redis)
