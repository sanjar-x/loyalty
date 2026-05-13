"""TaskIQ worker entry point — image-storage dedicated.

Owns the consumer half of the image-processing pipeline (Pillow resize
+ S3 cleanup). The task bodies (``process_image_task`` and
``cleanup_orphans_task``) live next to this file in ``./tasks.py`` —
backend no longer carries them in its tree.

Backend dispatches by task name only via ``broker.kicker(...)`` (see
``apps/backend/src/modules/image/presentation/router_admin.py``); it
never imports ``tasks.py`` and therefore never registers these tasks
on its own broker. Only this worker subscribes to ``image.processing``
+ ``image.maintenance``.

The full bootstrap (container → setup_dishka → DLQ middleware →
task import) lives inline here rather than in
``apps/backend/src/bootstrap/``. Initialisation order is load-bearing:
``@broker.task()`` decorators in ``tasks.py`` capture the
middleware-attached broker state, so reordering breaks
``FromDishka[...]`` resolution.

Run command:

    cd apps/workers/image/storage && python -m taskiq worker main:broker
"""

from __future__ import annotations

import structlog
from dishka.async_container import AsyncContainer
from dishka.integrations.taskiq import setup_dishka
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import AsyncAdaptedQueuePool
from src.bootstrap.broker import broker
from src.bootstrap.config import settings
from src.bootstrap.container import create_container
from src.infrastructure.logging.dlq_middleware import DLQMiddleware
from taskiq.events import TaskiqEvents

logger = structlog.get_logger(__name__)

# 1. Container + Dishka middleware MUST be set up before tasks import.
container: AsyncContainer = create_container()
setup_dishka(container=container, broker=broker)

# 1.1 DLQ middleware persists failed task envelopes to the database.
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

# 2. Import the consumer task bodies. ``tasks`` is the sibling file in
#    this directory; ``python -m taskiq worker`` puts the cwd on
#    ``sys.path[0]``, so it resolves as a top-level module.
import tasks  # noqa: E402, F401


@broker.on_event(TaskiqEvents.WORKER_STARTUP)
async def startup_event(state) -> None:
    """image-storage worker startup hook — stores container in state."""
    logger.info("image-storage TaskIQ Worker started and ready to process tasks")
    state.dishka_container = container


@broker.on_event(TaskiqEvents.WORKER_SHUTDOWN)
async def shutdown_event(state) -> None:
    """image-storage worker shutdown hook — closes Dishka container."""
    logger.info("Shutting down image-storage TaskIQ Worker...")
    if hasattr(state, "dishka_container"):
        await state.dishka_container.close()
        logger.info("Dishka DI container closed successfully")


__all__ = ["broker"]
