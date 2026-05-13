"""TaskIQ entry point for the ``apps/workers/image/rmbg`` artefact.

Owns the Bria RMBG-2.0 background-removal consumer. Fully independent
from backend — coordination is via shared PostgreSQL rows, Redis
Streams wire format, and RabbitMQ queue / task names.

Eager-import torch / torchvision / timm / kornia on the main thread
BEFORE the broker imports task bodies. This sidesteps the
``torchvision::nms already has DispatchKey::Meta implementation``
RuntimeError observed in prod (2026-05-12): when ``transformers``
re-imports torchvision inside an asyncio worker thread,
``_meta_registrations.py`` attempts a second ``_register_fake`` which
torch ≥ 2.4 rejects. Importing those modules here ensures the
registration happens exactly once in the main interpreter, and
subsequent worker-thread imports hit ``sys.modules`` cache.

Run command:

    cd apps/workers/image/rmbg && python -m taskiq worker main:broker
"""

from __future__ import annotations

# 1. Eager-import the heavy ML stack on the main thread.
import torch  # noqa: F401, E402
import torchvision  # noqa: F401, E402
import timm  # noqa: F401, E402
import kornia  # noqa: F401, E402

import structlog  # noqa: E402
from taskiq.events import TaskiqEvents  # noqa: E402

from broker import broker  # noqa: E402
from db import engine  # noqa: E402
from redis_client import redis_client  # noqa: E402

# Side-effect import — registers ``remove_background_task`` on the
# broker. Must run BEFORE TaskIQ's worker process scans the broker
# for registered tasks.
import tasks  # noqa: E402, F401

logger = structlog.get_logger(__name__)


@broker.on_event(TaskiqEvents.WORKER_STARTUP)
async def startup_event(state) -> None:
    logger.info("image-rmbg TaskIQ worker started")


@broker.on_event(TaskiqEvents.WORKER_SHUTDOWN)
async def shutdown_event(state) -> None:
    logger.info("Shutting down image-rmbg TaskIQ worker...")
    await redis_client.aclose()
    await engine.dispose()


__all__ = ["broker"]
