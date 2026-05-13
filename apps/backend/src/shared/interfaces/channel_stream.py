"""Channel stream port (Hexagonal Architecture).

Defines the ``IChannelStream`` protocol for fan-out of JSON-shaped events
on named channels. Concrete implementation lives in the infrastructure
layer (Redis Streams). Consumers (image SSE manager, catalog SKU
pricing pub/sub) depend on this protocol only.

Differs from a fire-and-forget pub/sub in two ways that the
``Last-Event-ID`` SSE flow relies on:

1. **Persistence.** Each ``publish`` lands an entry in a bounded log;
   late subscribers (e.g. reconnecting after a network blip) still see
   the message as long as it sits within the retention window.

2. **Replay.** ``subscribe(start_id=...)`` resumes from any prior event
   ID, so the SSE handler can honor the ``Last-Event-ID`` HTTP header
   that browsers send on automatic reconnect — no missed terminal
   status updates.

Typical wiring:

    class SSEManager:
        def __init__(self, stream: IChannelStream) -> None:
            self._stream = stream

        async def publish(self, sid: UUID, data: dict) -> str:
            return await self._stream.publish(f"media:status:{sid}", data)

        async def subscribe(self, sid: UUID, *, last_event_id: str | None):
            start = last_event_id or "$"  # "$" = only new entries
            async for event in self._stream.subscribe(
                f"media:status:{sid}", start_id=start, timeout=120.0
            ):
                ...
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class StreamEvent:
    """One entry from a stream subscription.

    ``id`` is the underlying log's monotonic entry identifier (e.g.
    Redis Streams gives ``"1715608800123-0"``). Pass it back as
    ``start_id`` on the next ``subscribe`` call to resume after a
    disconnect — the SSE wire format carries this in ``id:`` lines and
    the browser echoes it back via the ``Last-Event-ID`` request
    header.
    """

    id: str
    data: dict[str, Any]


class IChannelStream(Protocol):
    """Contract for persistent, replayable channel fan-out."""

    async def publish(self, channel: str, data: dict[str, Any]) -> str:
        """Append ``data`` to ``channel`` and return its entry ID.

        Implementations are expected to enforce a bounded retention
        (size-based ``MAXLEN`` plus optional inactivity TTL) so a
        long-running channel does not grow without limit.
        """
        ...

    def subscribe(
        self,
        channel: str,
        *,
        start_id: str = "$",
        timeout: float,
        poll_interval: float = 1.0,
    ) -> AsyncGenerator[StreamEvent | None]:
        """Yield entries from ``channel`` until ``timeout`` elapses.

        Args:
            channel: Logical channel name (e.g. ``"media:status:<uuid>"``).
            start_id: Resume point. ``"$"`` (default) reads only entries
                appended **after** the call begins — the right value
                for a brand-new subscription. ``"0"`` reads from the
                beginning of the retained log. A specific previously-
                yielded ``StreamEvent.id`` reads everything appended
                strictly after that entry — the right value for an SSE
                ``Last-Event-ID`` resume.
            timeout: Total seconds to keep the subscription open.
                Callers reconnect for longer sessions; framing the
                budget here keeps the async generator's lifecycle
                bounded.
            poll_interval: Idle-tick budget. Implementations yield
                ``None`` whenever ``poll_interval`` elapses without a
                message, so the SSE handler can emit a keepalive comment
                frame and the caller can decide whether to keep waiting.

        Yields:
            ``StreamEvent`` for each delivered entry, in order.
            ``None`` on every idle ``poll_interval`` tick.
        """
        ...
