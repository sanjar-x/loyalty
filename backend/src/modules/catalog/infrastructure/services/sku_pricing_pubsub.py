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

import structlog
from redis.asyncio import Redis
from redis.exceptions import RedisError

logger = structlog.get_logger(__name__)


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

        Errors:
            * Per-message ``json.JSONDecodeError`` is logged and the
              loop continues — one malformed payload (e.g. publisher
              regression, manual ``redis-cli publish``) must NOT take
              down every admin watching the same product.
            * ``RedisError`` (Redis connection drop, broker outage)
              propagates so the SSE route can emit an ``error`` frame
              and let the client auto-reconnect.
        """
        channel = self.channel_name(product_id)
        log = logger.bind(channel=channel, product_id=str(product_id))
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
                        # One bad payload must not blackhole the channel
                        # for every admin connected. Log & continue —
                        # the next valid message resumes normal flow.
                        raw = msg.get("data")
                        log.warning(
                            "sse_pubsub_malformed_payload",
                            raw=str(raw)[:200] if raw is not None else None,
                        )
                        continue
                    yield data
                else:
                    yield None
        finally:
            # Cleanup must NOT mask an in-flight exception (e.g. the
            # original Redis outage triggers both the loop error AND a
            # secondary error inside aclose). Each step in its own
            # try/except so the original traceback is preserved.
            try:
                await pubsub.unsubscribe(channel)
            except (RedisError, OSError) as exc:
                log.warning("sse_pubsub_unsubscribe_failed", error=str(exc))
            try:
                await pubsub.aclose()
            except (RedisError, OSError) as exc:
                log.warning("sse_pubsub_aclose_failed", error=str(exc))
