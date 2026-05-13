"""Channel-stream fan-out for SKU pricing status updates (CAT-005).

Per-product fan-out of recompute outcomes from the outbox-driven
consumer to admin SSE subscribers. Channel naming and payload shape
are catalog-specific concerns and live here; the low-level streaming
plumbing (XADD/XREAD, JSON, error handling, retention bounds) is
composed from
:class:`src.shared.interfaces.channel_stream.IChannelStream` so a fix
to the streaming layer lands once and benefits every module that needs
SSE fan-out.

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

from src.shared.interfaces.channel_stream import IChannelStream, StreamEvent


class SkuPricingPubsub:
    """Per-product pricing-status fan-out via the workspace channel stream."""

    def __init__(self, stream: IChannelStream) -> None:
        self._stream = stream

    @staticmethod
    def channel_name(product_id: uuid.UUID) -> str:
        return f"catalog:sku-pricing:{product_id}"

    async def publish(self, product_id: uuid.UUID, data: dict) -> str:
        """Fan out a status update to all admin clients watching this product."""
        return await self._stream.publish(self.channel_name(product_id), data)

    async def subscribe(
        self,
        product_id: uuid.UUID,
        *,
        last_event_id: str | None = None,
        timeout: float = 600.0,
        poll_interval: float = 1.0,
    ) -> AsyncGenerator[StreamEvent | None]:
        """Yield ``StreamEvent``s pushed to this product's channel.

        ``last_event_id`` is the SSE resume point (mirror of the
        ``Last-Event-ID`` HTTP header). ``None`` (fresh connection)
        reads only new entries; a previously delivered
        ``StreamEvent.id`` replays everything appended after that
        point — useful when a long admin session reconnects after a
        network blip without losing in-flight pricing ticks.

        Yields ``None`` when no message arrived within
        ``poll_interval`` — gives the SSE handler a chance to send a
        comment-frame keepalive on idle connections (FastAPI's
        ``EventSourceResponse(ping=N)`` also does this at the transport
        level). Stops after ``timeout`` seconds — callers reconnect for
        longer-running admin sessions.

        Error semantics (Redis outage, malformed payload, cleanup) are
        owned by the underlying :class:`IChannelStream` binding.
        """
        start_id = last_event_id or "$"
        async for event in self._stream.subscribe(
            self.channel_name(product_id),
            start_id=start_id,
            timeout=timeout,
            poll_interval=poll_interval,
        ):
            yield event
