"""SSE status streaming via Redis pub/sub.

Owned by the image module because the channel-name convention
(``media:status:<id>``) is image-specific and the published payload
shape (``StatusEventData``) is part of the image module's API
contract. Concrete because the Redis dependency is the only sensible
implementation we have today.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from collections.abc import AsyncGenerator

import structlog
from redis.asyncio import Redis
from redis.exceptions import RedisError

logger = structlog.get_logger(__name__)


class SSEManager:
    """Publish/subscribe channel for storage object processing status."""

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

        Yields ``None`` when no message arrived within ``poll_interval``
        — caller decides whether to keep waiting or break. Stops after
        ``timeout`` seconds or on terminal status (``completed`` /
        ``failed``).

        Keep-alive pings are NOT sent here — :class:`EventSourceResponse`
        handles them at the transport level.

        Errors:
            * Per-message ``json.JSONDecodeError`` is logged and the
              loop continues — one malformed payload must NOT take
              down every client watching the same storage object.
            * ``RedisError`` (Redis connection drop, broker outage)
              propagates so the SSE route can emit an ``error`` frame
              and let the client auto-reconnect.
        """
        channel = self.channel_name(storage_object_id)
        log = logger.bind(channel=channel, storage_object_id=str(storage_object_id))
        pubsub = self._redis.pubsub()
        try:
            await pubsub.subscribe(channel)
        except RedisError, OSError:
            log.exception("sse_pubsub_subscribe_failed")
            raise

        try:
            deadline = asyncio.get_running_loop().time() + timeout
            while asyncio.get_running_loop().time() < deadline:
                try:
                    msg = await pubsub.get_message(
                        ignore_subscribe_messages=True,
                        timeout=poll_interval,
                    )
                except RedisError, OSError:
                    log.exception("sse_pubsub_poll_failed")
                    raise

                if msg and msg["type"] == "message":
                    try:
                        data = json.loads(msg["data"])
                    except json.JSONDecodeError, UnicodeDecodeError, TypeError:
                        raw = msg.get("data")
                        log.warning(
                            "sse_pubsub_malformed_payload",
                            raw=str(raw)[:200] if raw is not None else None,
                        )
                        continue
                    yield data
                    if data.get("status") in ("completed", "failed"):
                        return
                else:
                    yield None
        finally:
            try:
                await pubsub.unsubscribe(channel)
            except (RedisError, OSError) as exc:
                log.warning("sse_pubsub_unsubscribe_failed", error=str(exc))
            try:
                await pubsub.aclose()
            except (RedisError, OSError) as exc:
                log.warning("sse_pubsub_aclose_failed", error=str(exc))
