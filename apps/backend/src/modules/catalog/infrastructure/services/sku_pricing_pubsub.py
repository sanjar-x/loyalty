"""Redis pub/sub for SKU pricing status updates (CAT-005, REC-029).

Per-product fan-out of recompute outcomes from the outbox-driven
consumer to admin SSE subscribers. Channel naming and payload shape
are catalog-specific concerns and live here; the low-level Redis
plumbing (subscribe loop, JSON, error handling, cleanup) is composed
from :class:`src.shared.infrastructure.redis_pubsub.RedisChannelStream`
so a fix to the streaming layer lands once and benefits every module
that needs SSE fan-out.

Channel naming: ``catalog:sku-pricing:{product_id}``.

Payload shape (JSON):

    {
      "skuId": "...",
      "pricingStatus": "priced" | "stale_fx" | ...,
      "sellingPrice": { "amount": 13750, "currency": "RUB" } | null,
      "pricedAt": "2026-05-08T09:30:00+00:00" | null,
      "pricedFailureReason": "..." | null
    }
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator

from redis.asyncio import Redis

from src.shared.infrastructure.redis_pubsub import RedisChannelStream


class SkuPricingPubsub:
    """Per-product pricing-status pub/sub via Redis."""

    def __init__(self, redis: Redis) -> None:
        self._stream = RedisChannelStream(redis)

    @staticmethod
    def channel_name(product_id: uuid.UUID) -> str:
        return f"catalog:sku-pricing:{product_id}"

    async def publish(self, product_id: uuid.UUID, data: dict) -> None:
        """Fan out a status update to all admin clients watching this product."""
        await self._stream.publish(self.channel_name(product_id), data)

    async def subscribe(
        self,
        product_id: uuid.UUID,
        *,
        timeout: float = 600.0,
        poll_interval: float = 1.0,
    ) -> AsyncGenerator[dict | None]:
        """Yield status dicts pushed to this product's channel.

        Yields ``None`` when no message arrived within ``poll_interval`` —
        gives the SSE handler a chance to send a comment-frame keepalive
        on idle connections (FastAPI's ``EventSourceResponse(ping=N)``
        also does this at the transport level).

        Stops after ``timeout`` seconds. Caller must reconnect for
        longer-running admin sessions.

        Error semantics (Redis outage, malformed payload, cleanup) are
        owned by :class:`RedisChannelStream`.
        """
        async for msg in self._stream.subscribe(
            self.channel_name(product_id),
            timeout=timeout,
            poll_interval=poll_interval,
        ):
            yield msg
