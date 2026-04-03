"""SSE status streaming via Redis pub/sub."""

from __future__ import annotations

import asyncio
import json
import uuid
from collections.abc import AsyncGenerator

from redis.asyncio import Redis


class SSEManager:
    """Publish/subscribe for storage object processing status."""

    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    def channel_name(self, storage_object_id: uuid.UUID) -> str:
        return f"media:status:{storage_object_id}"

    async def publish(self, storage_object_id: uuid.UUID, data: dict) -> None:
        channel = self.channel_name(storage_object_id)
        await self._redis.publish(channel, json.dumps(data))

    async def subscribe(
        self,
        storage_object_id: uuid.UUID,
        *,
        timeout: float = 120.0,
        poll_interval: float = 1.0,
    ) -> AsyncGenerator[dict | None]:
        """Yield status dicts from Redis pub/sub.

        Yields ``None`` when no message arrived within *poll_interval*
        (caller decides whether to keep waiting or break).
        Automatically stops after *timeout* seconds or on terminal status.

        Keep-alive pings are NOT sent here — ``EventSourceResponse(ping=N)``
        handles that at the transport level.
        """
        channel = self.channel_name(storage_object_id)
        pubsub = self._redis.pubsub()
        await pubsub.subscribe(channel)
        try:
            deadline = asyncio.get_running_loop().time() + timeout
            while asyncio.get_running_loop().time() < deadline:
                msg = await pubsub.get_message(
                    ignore_subscribe_messages=True,
                    timeout=poll_interval,
                )
                if msg and msg["type"] == "message":
                    data = json.loads(msg["data"])
                    yield data
                    if data.get("status") in ("completed", "failed"):
                        return
                else:
                    yield None  # no message yet
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.aclose()
