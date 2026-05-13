"""TaskIQ worker entry point — image-rmbg dedicated.

Owns the consumer half of the Bria RMBG-2.0 background-removal
pipeline. The task body (``remove_background_task``) lives next to
this file in ``./tasks.py``; backend dispatches by task name only via
``broker.kicker().with_task_name("remove_background").kiq(...)`` and
never imports the body. Only this worker subscribes to ``image.ml``.

Eager-import the heavy ML stack on the main thread BEFORE container
setup or task imports. This sidesteps the
``torchvision::nms already has DispatchKey::Meta implementation``
RuntimeError observed in prod (2026-05-12 incident): when
``transformers`` re-imports torchvision inside an asyncio worker
thread, ``_meta_registrations.py`` attempts a second
``_register_fake`` which torch ≥ 2.4 rejects. Importing torch /
torchvision / timm / kornia here forces the registration to happen
exactly once in the main interpreter; subsequent worker-thread
imports hit ``sys.modules`` cache.

Bootstrap order is load-bearing (matches the image-storage worker):
ML eager-imports → container → setup_dishka → DLQ middleware → task
import → lifecycle hooks. ``@broker.task()`` in ``tasks.py`` captures
the middleware-attached broker state, so reordering breaks
``FromDishka[...]`` resolution at runtime.

Run command:

    cd apps/workers/image/rmbg && python -m taskiq worker main:broker
"""

from __future__ import annotations

import kornia  # noqa: F401, E402
import structlog  # noqa: E402
import timm  # noqa: F401, E402

# 1. Eager-import the heavy ML stack on the main thread. Order matters:
#    torch first (registers core ops), then torchvision (extends with
#    NMS / RoI), then timm (pulls torchvision.models.feature_extraction).
import torch  # noqa: F401, E402
import torchvision  # noqa: F401, E402
from dishka.async_container import AsyncContainer  # noqa: E402
from dishka.integrations.taskiq import setup_dishka  # noqa: E402
from sqlalchemy.ext.asyncio import (  # noqa: E402
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import AsyncAdaptedQueuePool  # noqa: E402
from src.bootstrap.broker import broker  # noqa: E402
from src.bootstrap.config import settings  # noqa: E402
from src.bootstrap.container import create_container  # noqa: E402
from src.infrastructure.logging.dlq_middleware import DLQMiddleware  # noqa: E402
from taskiq.events import TaskiqEvents  # noqa: E402

logger = structlog.get_logger(__name__)

# 2. Container + Dishka middleware MUST be set up before tasks import.
container: AsyncContainer = create_container()
setup_dishka(container=container, broker=broker)

# 2.1 DLQ middleware persists failed task envelopes to the database.
_dlq_engine = create_async_engine(
    url=settings.database_url,
    poolclass=AsyncAdaptedQueuePool,
    pool_size=2,
    max_overflow=1,
    pool_pre_ping=True,
)
_dlq_session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=_dlq_engine, autoflush=False, expire_on_commit=False
)
broker.add_middlewares(DLQMiddleware(session_factory=_dlq_session_factory))

# 3. Import the consumer task body. ``tasks`` is the sibling file in
#    this directory; ``python -m taskiq worker`` puts the cwd on
#    ``sys.path[0]``, so it resolves as a top-level module.
import tasks  # noqa: E402, F401


@broker.on_event(TaskiqEvents.WORKER_STARTUP)
async def startup_event(state) -> None:
    """image-rmbg worker startup hook — stores container in state."""
    logger.info("image-rmbg TaskIQ Worker started and ready to process tasks")
    state.dishka_container = container


@broker.on_event(TaskiqEvents.WORKER_SHUTDOWN)
async def shutdown_event(state) -> None:
    """image-rmbg worker shutdown hook — closes Dishka container."""
    logger.info("Shutting down image-rmbg TaskIQ Worker...")
    if hasattr(state, "dishka_container"):
        await state.dishka_container.close()
        logger.info("Dishka DI container closed successfully")


__all__ = ["broker"]
