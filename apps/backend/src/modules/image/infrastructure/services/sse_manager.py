"""SSE status streaming for image processing.

Owned by the image module because the channel-name convention
(``media:status:<id>``) is image-specific and the published
``StatusEventData`` shape is part of the image module's API contract.
Low-level streaming plumbing (XADD/XREAD, JSON, error handling, idle
ticks, retention bounds) is composed from
:class:`src.shared.interfaces.channel_stream.IChannelStream` so a fix
to the streaming layer lands once and benefits every module.

Image-specific semantics that stay here: the ``subscribe`` loop
terminates on ``status in (completed, failed)`` because image
processing is short-lived terminal-state — the catalog pricing stream
runs the full admin session and would not benefit from this rule.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator

from src.shared.interfaces.channel_stream import IChannelStream, StreamEvent


class SSEManager:
    """Publish/subscribe channel for storage-object processing status."""

    def __init__(self, stream: IChannelStream) -> None:
        self._stream = stream

    def channel_name(self, storage_object_id: uuid.UUID) -> str:
        return f"media:status:{storage_object_id}"

    async def publish(self, storage_object_id: uuid.UUID, data: dict) -> str:
        """Append a status payload and return its event ID."""
        return await self._stream.publish(self.channel_name(storage_object_id), data)

    async def subscribe(
        self,
        storage_object_id: uuid.UUID,
        *,
        last_event_id: str | None = None,
        timeout: float = 120.0,
        poll_interval: float = 1.0,
    ) -> AsyncGenerator[StreamEvent | None]:
        """Yield ``StreamEvent``s for this storage object's status channel.

        ``last_event_id`` is the SSE resume point (mirror of the
        ``Last-Event-ID`` HTTP header the browser sends on
        ``EventSource`` reconnect). ``None`` (fresh connection) reads
        only new entries; a previously delivered ``StreamEvent.id``
        replays everything appended after that point — terminal frames
        that landed during a network blip are no longer lost.

        Yields ``None`` whenever ``poll_interval`` elapses without a
        message so the SSE route can emit a keepalive comment frame.
        Stops after ``timeout`` seconds OR on terminal status
        (``completed`` / ``failed``) — image processing is one-shot, so
        the loop closes itself once the storage object reaches a
        terminal state.

        Error semantics (Redis outage, malformed payload, cleanup) are
        owned by the underlying :class:`IChannelStream` binding.
        """
        start_id = last_event_id or "$"
        async for event in self._stream.subscribe(
            self.channel_name(storage_object_id),
            start_id=start_id,
            timeout=timeout,
            poll_interval=poll_interval,
        ):
            if event is None:
                yield None
                continue
            yield event
            if event.data.get("status") in ("completed", "failed"):
                return
