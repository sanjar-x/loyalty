"""Redis pub/sub for SKU pricing status updates (CAT-005).

Pushes recompute outcomes from the outbox-driven consumer into a
per-product channel so admin UI's SSE subscription can render status
changes without polling. Same channel-name + iterator-yielding contract
as the image module's :class:`SSEManager`, but specialised to
catalog's per-product pricing-status events.

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

import asyncio
import json
import uuid
from collections.abc import AsyncGenerator

from redis.asyncio import Redis


class SkuPricingPubsub:
    """Per-product pricing-status pub/sub via Redis."""

    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    @staticmethod
    def channel_name(product_id: uuid.UUID) -> str:
        return f"catalog:sku-pricing:{product_id}"

    async def publish(self, product_id: uuid.UUID, data: dict) -> None:
        """Fan out a status update to all admin clients watching this product."""
        await self._redis.publish(self.channel_name(product_id), json.dumps(data))

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
        """
        channel = self.channel_name(product_id)
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
                    yield json.loads(msg["data"])
                else:
                    yield None
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.aclose()
