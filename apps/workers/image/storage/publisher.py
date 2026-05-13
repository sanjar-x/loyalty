"""Image-storage worker's status publisher — local infrastructure.

Writes directly to Redis Streams (``XADD``) with no dependency on
backend's ``IChannelStream`` Protocol or ``SSEManager`` wrapper —
the worker owns its publish path end to end. Backend's SSE endpoint
subscribes to the same channel format (``media:status:{uuid}``) via
its own ``XREAD`` loop; the wire format (entries with a JSON-encoded
``data`` field, ``MAXLEN ~ 1000``, idle TTL via per-publish
``EXPIRE``) is the contract between the two sides.

Why local rather than shared:
* Worker has zero coupling to backend's streaming primitive — fewer
  imports, smaller transitive graph.
* Channel naming convention (``media:status:{uuid}``) is the only
  cross-process protocol that has to match the subscriber; keeping
  it on both sides as a one-liner is cheaper than a shared package.
* Tuning knobs (retention, idle TTL) are owned per-publisher so each
  worker can size its log to its own access pattern.
"""

from __future__ import annotations

import json
import uuid
from typing import Any

import structlog
from redis.asyncio import Redis
from redis.exceptions import RedisError

logger = structlog.get_logger(__name__)

# Bound retention: 1 000 entries × ~256 B/entry ≈ 256 KB ceiling per
# channel. Image-processing channels are short-lived (~5 status frames
# per upload), so this is generous.
_MAXLEN = 1000

# Idle TTL: an unwatched channel reaps itself this long after the
# last publish. 1 h outlasts a network blip + SSE reconnect (browsers
# retry within 3 s) while still expiring abandoned channels promptly.
_IDLE_TTL_SECONDS = 3600

# Field name inside each stream entry. Single ``data`` field carrying
# the full JSON payload — matches what backend's ``RedisStreamChannel``
# subscribes for, so reader and writer stay symmetric.
_PAYLOAD_FIELD = "data"


def _coerce_str(value: bytes | str | memoryview) -> str:
    """Decode a Redis response value into ``str``."""
    if isinstance(value, str):
        return value
    if isinstance(value, memoryview):
        value = value.tobytes()
    return value.decode("utf-8")


class StatusPublisher:
    """Direct ``XADD``-based publisher for image-storage status updates."""

    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    @staticmethod
    def channel(storage_object_id: uuid.UUID) -> str:
        return f"media:status:{storage_object_id}"

    async def publish(
        self,
        storage_object_id: uuid.UUID,
        data: dict[str, Any],
    ) -> str:
        """Append a status payload and arm the idle-TTL.

        Returns the assigned entry ID (e.g. ``"1715608800123-0"``) —
        kept for symmetry with backend's publisher contract. Workers
        currently discard.
        """
        channel = self.channel(storage_object_id)
        log = logger.bind(channel=channel)
        try:
            entry_id = await self._redis.xadd(
                channel,
                {_PAYLOAD_FIELD: json.dumps(data)},
                maxlen=_MAXLEN,
                approximate=True,
            )
            # Re-arm idle expiry on every publish. Independent of XADD
            # so a primary publish that succeeds doesn't roll back if
            # the secondary EXPIRE drops (worst case the key lives
            # forever, which the MAXLEN cap still bounds).
            try:
                await self._redis.expire(channel, _IDLE_TTL_SECONDS)
            except RedisError as exc:
                log.warning("redis_stream_expire_failed", error=str(exc))
            return _coerce_str(entry_id)
        except RedisError:
            log.exception("redis_stream_publish_failed")
            raise
