"""Generic Redis pub/sub stream helper for SSE-style fan-out.

Owns the low-level Redis pumb/sub plumbing — channel subscribe/poll
loop, JSON encode/decode, error classification, cleanup-without-masking
— so module-specific wrappers (catalog SKU pricing, image processing
status, …) can stay thin and only carry their own bounded-context
concerns: channel naming, payload shape, terminal-state semantics.

Decoupling rationale (REC-029):

* ``src/shared/`` MUST NOT depend on any module — and this helper has
  no module-specific knowledge. It speaks ``str`` channel name and
  ``dict`` payload, nothing else.
* Each module-level wrapper composes :class:`RedisChannelStream`
  rather than re-implementing the loop. A bug fix to error handling,
  cleanup semantics, or malformed-payload handling lands once and
  every consumer benefits — exactly the regression CAT-016 had to
  duplicate across two files.
* The ``timeout`` knob stays on the per-call ``subscribe`` API
  (different consumers want different idle budgets — image processing
  is short-lived terminal-state, catalog pricing runs the full admin
  session).
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncGenerator

import structlog
from redis.asyncio import Redis
from redis.exceptions import RedisError

logger = structlog.get_logger(__name__)


class RedisChannelStream:
    """Bare Redis pub/sub helper for an SSE-style ``async for`` consumer.

    ``publish(channel, data)`` JSON-encodes and PUBLISHes once.
    ``subscribe(channel, *, timeout, poll_interval)`` yields decoded
    dicts as messages arrive, plus ``None`` on each idle poll so the
    caller can emit transport-level keepalives. Stops after ``timeout``
    seconds. Caller is responsible for the outer ``EventSourceResponse``
    framing.
    """

    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def publish(self, channel: str, data: dict) -> None:
        """JSON-encode and PUBLISH a single payload to ``channel``."""
        await self._redis.publish(channel, json.dumps(data))

    async def subscribe(
        self,
        channel: str,
        *,
        timeout: float,
        poll_interval: float = 1.0,
    ) -> AsyncGenerator[dict | None]:
        """Yield decoded payloads from ``channel`` until ``timeout`` elapses.

        Yields ``None`` whenever ``poll_interval`` elapses without a
        message — gives the SSE handler a chance to send a keepalive
        comment frame on idle connections.

        Errors:
            * Per-message ``json.JSONDecodeError`` is logged at warning
              level and the loop continues — one malformed payload
              (publisher regression, manual ``redis-cli publish``)
              must not blackhole the channel for every connected
              consumer.
            * ``RedisError`` (connection drop, broker outage) propagates
              so the route can emit an ``error`` SSE frame and let the
              client auto-reconnect.

        Cleanup:
            ``unsubscribe`` and ``aclose`` are wrapped in independent
            try/except blocks so a secondary Redis error during cleanup
            never masks the original outage in the traceback.
        """
        log = logger.bind(channel=channel)
        pubsub = self._redis.pubsub()
        try:
            await pubsub.subscribe(channel)
        except RedisError, OSError:
            log.exception("redis_pubsub_subscribe_failed")
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
                    log.exception("redis_pubsub_poll_failed")
                    raise

                if msg and msg["type"] == "message":
                    try:
                        data = json.loads(msg["data"])
                    except json.JSONDecodeError, UnicodeDecodeError, TypeError:
                        # One bad payload must not blackhole the channel
                        # for every consumer. Log & continue — the next
                        # valid message resumes normal flow.
                        raw = msg.get("data")
                        log.warning(
                            "redis_pubsub_malformed_payload",
                            raw=str(raw)[:200] if raw is not None else None,
                        )
                        continue
                    yield data
                else:
                    yield None
        finally:
            try:
                await pubsub.unsubscribe(channel)
            except (RedisError, OSError) as exc:
                log.warning("redis_pubsub_unsubscribe_failed", error=str(exc))
            try:
                await pubsub.aclose()
            except (RedisError, OSError) as exc:
                log.warning("redis_pubsub_aclose_failed", error=str(exc))
