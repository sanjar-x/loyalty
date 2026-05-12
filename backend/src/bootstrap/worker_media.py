"""TaskIQ worker entry point — media domain dedicated.

Mirrors :mod:`src.bootstrap.worker` but imports ONLY the image module's
task module. This narrows the worker's subscription to the
``image_processing`` / ``image_maintenance`` / ``image_ml`` queues —
the dedicated ``media-worker`` Railway service no longer round-robins
logistics / order / payment / activity / outbox tasks with the
``core-worker`` service.

Naming note: ``media`` is the broader semantic — the worker handles
image processing today, and is the natural home for future video /
audio pipelines without another rename.

Why a separate bootstrap rather than ``worker.py`` + a CLI flag: TaskIQ
``taskiq worker`` discovers queue subscriptions through whichever tasks
are registered on the broker at import time. Filtering at runtime is
not exposed by the current CLI (verified `taskiq worker --help` —
no ``--queue`` flag). The cheapest correct solution is a sibling
bootstrap module that imports a minimal task set.

Initialization order rules are identical to ``worker.py``:
    1. ``broker``        — created in ``src/bootstrap/broker.py``.
    2. ``container``     — Dishka DI container.
    3. ``setup_dishka()``— registers ``DishkaMiddleware`` on the broker.
    4. ``import tasks``  — tasks register via ``@broker.task()``.

The ``@broker.task()`` decorator captures the middleware-attached
broker state, so reordering imports breaks ``FromDishka[...]``
resolution at runtime. Keep ``noqa: E402`` to stop auto-formatters
from hoisting the task import.
"""

import structlog
from dishka.async_container import AsyncContainer
from dishka.integrations.taskiq import setup_dishka
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import AsyncAdaptedQueuePool
from taskiq.events import TaskiqEvents

from src.bootstrap.broker import broker
from src.bootstrap.config import settings
from src.bootstrap.container import create_container
from src.infrastructure.logging.dlq_middleware import DLQMiddleware

logger = structlog.get_logger(__name__)

# 1. Initialise the container and DI integration BEFORE importing tasks.
#    Identical to ``worker.py``.
container: AsyncContainer = create_container()
setup_dishka(container=container, broker=broker)

# 1.1 DLQ Middleware: persists failed tasks to the database.
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

# 2. Import ONLY image module tasks. This is the difference from
#    ``worker.py`` — no MODULES iteration, no outbox tasks.
#    Subscribed queues after this import:
#       * ``image_processing``  — Pillow resize variants
#       * ``image_maintenance`` — orphan cleanup cron
#       * ``image_ml``          — Bria RMBG-2.0 (gated on BG_REMOVAL_ENABLED)

import src.modules.image.infrastructure.tasks  # noqa: E402, F401


@broker.on_event(TaskiqEvents.WORKER_STARTUP)
async def startup_event(state) -> None:
    """Media worker startup hook — stores container in state."""
    logger.info("media TaskIQ Worker started and ready to process tasks")
    state.dishka_container = container


@broker.on_event(TaskiqEvents.WORKER_SHUTDOWN)
async def shutdown_event(state) -> None:
    """Media worker shutdown hook — closes Dishka container."""
    logger.info("Shutting down media TaskIQ Worker...")
    if hasattr(state, "dishka_container"):
        await state.dishka_container.close()
        logger.info("Dishka DI container closed successfully")
