"""Image-rmbg worker's status publisher — local infrastructure.

Mirror of ``apps/workers/image/storage/publisher.py``. Same wire
contract (``media:status:{uuid}`` channel, JSON-encoded ``data``
field, ``MAXLEN ~ 1000``, idle TTL via ``EXPIRE``) so backend's SSE
endpoint can consume from either worker indistinguishably.

Kept as a local module rather than imported from the storage sibling
because workers are independent deployables; sharing publish helpers
across worker packages would re-introduce the cross-package coupling
this refactor is meant to remove.
"""

from __future__ import annotations

import json
import uuid
from typing import Any

import structlog
from redis.asyncio import Redis
from redis.exceptions import RedisError

logger = structlog.get_logger(__name__)

_MAXLEN = 1000
_IDLE_TTL_SECONDS = 3600
_PAYLOAD_FIELD = "data"


def _coerce_str(value: bytes | str | memoryview) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, memoryview):
        value = value.tobytes()
    return value.decode("utf-8")


class StatusPublisher:
    """Direct ``XADD``-based publisher for image-rmbg status updates."""

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
        channel = self.channel(storage_object_id)
        log = logger.bind(channel=channel)
        try:
            entry_id = await self._redis.xadd(
                channel,
                {_PAYLOAD_FIELD: json.dumps(data)},
                maxlen=_MAXLEN,
                approximate=True,
            )
            try:
                await self._redis.expire(channel, _IDLE_TTL_SECONDS)
            except RedisError as exc:
                log.warning("redis_stream_expire_failed", error=str(exc))
            return _coerce_str(entry_id)
        except RedisError:
            log.exception("redis_stream_publish_failed")
            raise
