"""SSE status streaming via Redis pub/sub (REC-029 refactor).

Owned by the image module because the channel-name convention
(``media:status:<id>``) is image-specific and the published
``StatusEventData`` shape is part of the image module's API contract.
Low-level Redis plumbing (subscribe loop, JSON, error handling,
cleanup) is composed from
:class:`shared.infrastructure.redis_pubsub.RedisChannelStream`
so a fix to the streaming layer lands once and benefits every module.

Image-specific semantics that stay here: the ``subscribe`` loop
terminates on ``status in (completed, failed)`` because image
processing is short-lived terminal-state — the catalog pricing stream
runs the full admin session and would not benefit from this rule.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator

from redis.asyncio import Redis

from shared.infrastructure.redis_pubsub import RedisChannelStream


class SSEManager:
    """Publish/subscribe channel for storage object processing status."""

    def __init__(self, redis: Redis) -> None:
        self._stream = RedisChannelStream(redis)

    def channel_name(self, storage_object_id: uuid.UUID) -> str:
        return f"media:status:{storage_object_id}"

    async def publish(self, storage_object_id: uuid.UUID, data: dict) -> None:
        await self._stream.publish(self.channel_name(storage_object_id), data)

    async def subscribe(
        self,
        storage_object_id: uuid.UUID,
        *,
        timeout: float = 120.0,
        poll_interval: float = 1.0,
    ) -> AsyncGenerator[dict | None]:
        """Yield status dicts from Redis pub/sub.

        Yields ``None`` whenever ``poll_interval`` elapses without a
        message — caller decides whether to keep waiting or break.
        Stops after ``timeout`` seconds OR on terminal status
        (``completed`` / ``failed``) — image processing is one-shot,
        so the loop closes itself once the storage object reaches a
        terminal state. Keep-alive pings are handled by the route's
        :class:`EventSourceResponse`.

        Error semantics (Redis outage, malformed payload, cleanup) are
        owned by :class:`RedisChannelStream`.
        """
        async for data in self._stream.subscribe(
            self.channel_name(storage_object_id),
            timeout=timeout,
            poll_interval=poll_interval,
        ):
            if data is None:
                yield None
                continue
            yield data
            if data.get("status") in ("completed", "failed"):
                return
