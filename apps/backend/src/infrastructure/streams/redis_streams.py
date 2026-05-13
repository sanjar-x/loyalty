"""Redis-Streams-backed implementation of :class:`IChannelStream`.

Why Streams, not pub/sub
========================

The previous ``RedisChannelStream`` used Redis ``PUBLISH`` / ``SUBSCRIBE``
which is fire-and-forget: a status update emitted while no SSE client
holds the channel disappears. That created a race against the
``EventSource`` auto-reconnect cycle — a worker finishing precisely
between a client's disconnect and reconnect lost the terminal frame
and left the UI hanging in ``processing``.

Redis Streams (``XADD``/``XREAD``) keep entries in a log with bounded
retention. The SSE endpoint reads the HTTP ``Last-Event-ID`` header on
reconnect and asks ``XREAD`` for everything after that ID — the
browser's standard reconnect contract finally has teeth.

Memory bound
============

Each ``publish`` runs ``XADD MAXLEN ~ <retention>`` so the per-channel
log is capped (default 1 000 entries, ~hundreds of KB per channel) and
``EXPIRE`` so a channel that goes idle disappears after
:data:`_IDLE_TTL_SECONDS`. There's no scheduled GC — every publish
re-arms the TTL, the absence of further publishes lets the key reap
itself.
"""

from __future__ import annotations

import asyncio
import json
import time
from collections.abc import AsyncGenerator
from typing import Any

import structlog
from redis.asyncio import Redis
from redis.exceptions import RedisError

from src.shared.interfaces.channel_stream import IChannelStream, StreamEvent

logger = structlog.get_logger(__name__)

# Bound each channel's retained log. 1 000 entries × ~256 B/entry ≈
# 256 KB ceiling per channel — fine for image processing flows
# (~5 status frames per upload) and admin pricing sessions
# (~minutes of slow ticks). Tune via constructor if a use case needs
# a different budget.
_DEFAULT_MAXLEN = 1000

# Idle-TTL: an unwatched channel reaps itself this long after the last
# publish. Long enough to outlast a network blip and SSE reconnect
# (browsers retry within 3 s by default), short enough that abandoned
# channels do not accumulate across hours of operation.
_IDLE_TTL_SECONDS = 3600

# Field name inside each stream entry. ``XADD`` accepts a flat
# field-value map; we serialise the whole payload into a single
# ``data`` field so the wire format mirrors what the pub/sub helper
# used to publish.
_PAYLOAD_FIELD = "data"


def _coerce_str(value: bytes | str | memoryview) -> str:
    """Decode a Redis response value into ``str`` regardless of client mode.

    The shared Redis client may or may not have ``decode_responses=True``
    enabled depending on how :class:`CacheProvider` is configured.
    Normalise here so this implementation works under either.
    """
    if isinstance(value, str):
        return value
    if isinstance(value, memoryview):
        value = value.tobytes()
    return value.decode("utf-8")


class RedisStreamChannel(IChannelStream):
    """Redis Streams binding for :class:`IChannelStream`."""

    def __init__(
        self,
        redis: Redis,
        *,
        maxlen: int = _DEFAULT_MAXLEN,
        idle_ttl_seconds: int = _IDLE_TTL_SECONDS,
    ) -> None:
        self._redis = redis
        self._maxlen = maxlen
        self._idle_ttl_seconds = idle_ttl_seconds

    async def publish(self, channel: str, data: dict[str, Any]) -> str:
        """Append a payload to ``channel`` and arm the idle-TTL.

        Returns the assigned entry ID (e.g. ``"1715608800123-0"``) so
        callers that emit SSE frames can echo it in ``id:`` lines.
        """
        log = logger.bind(channel=channel)
        try:
            entry_id = await self._redis.xadd(
                channel,
                {_PAYLOAD_FIELD: json.dumps(data)},
                maxlen=self._maxlen,
                approximate=True,
            )
            # Re-arm idle expiry on every publish. Independent of
            # XADD so a primary publish that succeeds doesn't roll
            # back if the secondary EXPIRE drops (the channel
            # already got its entry; worst case the key lives
            # forever in Redis, which the MAXLEN cap still bounds).
            try:
                await self._redis.expire(channel, self._idle_ttl_seconds)
            except RedisError as exc:
                log.warning("redis_stream_expire_failed", error=str(exc))
            return _coerce_str(entry_id)
        except RedisError:
            log.exception("redis_stream_publish_failed")
            raise

    async def subscribe(
        self,
        channel: str,
        *,
        start_id: str = "$",
        timeout: float,
        poll_interval: float = 1.0,
    ) -> AsyncGenerator[StreamEvent | None]:
        """Yield ``StreamEvent``s from ``channel`` until ``timeout`` elapses.

        ``start_id`` works exactly as Redis ``XREAD`` defines it: ``"$"``
        for new-entries-only (fresh SSE connection), ``"0"`` for the
        whole retained log, or a previously yielded ``StreamEvent.id``
        to resume after disconnect (SSE ``Last-Event-ID`` header).

        Idle ticks: every ``poll_interval`` seconds without a message
        the generator yields ``None`` so the SSE route can emit a
        comment-frame keepalive and the caller can check its
        outer deadline.
        """
        log = logger.bind(channel=channel)
        last_id = start_id
        deadline = time.monotonic() + timeout
        # ``XREAD BLOCK`` takes milliseconds; clamp poll_interval just
        # below the remaining-budget so we never block past ``timeout``.
        poll_ms = max(1, int(poll_interval * 1000))

        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return

            block_ms = min(poll_ms, max(1, int(remaining * 1000)))

            try:
                # ``count=None`` means "drain whatever is available".
                # ``XREAD`` returns ``None`` (not ``[]``) on timeout.
                entries = await self._redis.xread(
                    {channel: last_id},
                    block=block_ms,
                    count=None,
                )
            except RedisError:
                log.exception("redis_stream_xread_failed")
                raise
            except asyncio.CancelledError:
                # Generator was closed (client disconnect). Re-raise to
                # honour the cooperative cancellation contract.
                raise

            if not entries:
                yield None
                continue

            # entries shape: [(channel_name, [(entry_id, {field: value}), ...])]
            # We subscribe to a single channel, so the outer list has
            # exactly one element; iterate defensively anyway.
            for _channel_name, batch in entries:
                for raw_id, fields in batch:
                    entry_id = _coerce_str(raw_id)
                    last_id = entry_id
                    raw_payload = fields.get(_PAYLOAD_FIELD) or fields.get(
                        _PAYLOAD_FIELD.encode()
                    )
                    if raw_payload is None:
                        log.warning("redis_stream_payload_missing", id=entry_id)
                        continue
                    try:
                        data = json.loads(_coerce_str(raw_payload))
                    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                        # One bad payload must not blackhole the channel
                        # for every consumer. Log & continue — the next
                        # valid entry resumes normal flow.
                        log.warning(
                            "redis_stream_malformed_payload",
                            id=entry_id,
                            error=str(exc),
                        )
                        continue
                    yield StreamEvent(id=entry_id, data=data)
