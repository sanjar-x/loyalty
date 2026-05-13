"""TaskIQ entry point for the ``apps/workers/image/storage`` artefact.

Owns the consumer half of the image-processing pipeline (Pillow
resize + S3 cleanup). Fully independent from backend — no Python
import crosses the boundary; coordination is via shared
infrastructure (PostgreSQL row format, Redis Streams wire format,
RabbitMQ queue + task names).

Bootstrap order is load-bearing:
    1. ``broker`` from ``broker.py`` (TaskIQ broker singleton).
    2. ``import tasks`` — task bodies register on the broker via
       ``@broker.task``.
The worker startup hook below logs readiness; shutdown closes the
shared Redis connection and the DB engine pool.

Run command:

    cd apps/workers/image/storage && python -m taskiq worker main:broker
"""

from __future__ import annotations

import structlog
from taskiq.events import TaskiqEvents

from broker import broker
from db import engine
from redis_client import redis_client

# Side-effect import — registers ``image_process_task`` and
# ``image_cleanup_orphans_task`` on the broker. Must run BEFORE TaskIQ's
# worker process scans the broker for registered tasks.
import tasks  # noqa: E402, F401

logger = structlog.get_logger(__name__)


@broker.on_event(TaskiqEvents.WORKER_STARTUP)
async def startup_event(state) -> None:
    """Log readiness when TaskIQ's worker process is up."""
    logger.info("image-storage TaskIQ worker started")


@broker.on_event(TaskiqEvents.WORKER_SHUTDOWN)
async def shutdown_event(state) -> None:
    """Release the DB pool + Redis connection on shutdown."""
    logger.info("Shutting down image-storage TaskIQ worker...")
    await redis_client.aclose()
    await engine.dispose()


__all__ = ["broker"]
