"""TaskIQ worker entry point.

IMPORTANT: The initialisation order in this module is critical and must
not be changed.

Dependency graph at worker startup:
    1. ``broker``        -- created in ``src/bootstrap/broker.py`` (imported above).
    2. ``container``     -- Dishka DI container (``create_container()``).
    3. ``setup_dishka()``-- registers ``DishkaMiddleware`` on the broker.
    4. Module task imports -- tasks register themselves via the
       ``@broker.task()`` decorator and the outbox relay's
       ``register_event_handler`` helper. Both are import-time side
       effects.

Why this exact order?
    ``@broker.task()`` calls ``broker.register_task()`` at import time.
    ``DishkaMiddleware`` must already be attached to the broker at that
    point; otherwise ``FromDishka[...]`` dependencies will not resolve at
    execution time and the worker will crash with a runtime error.

Module discovery:
    Per-module task module paths come from each :class:`ModuleManifest`
    in :mod:`src.bootstrap.modules`. The framework-level outbox-tasks
    module is imported directly because it is not owned by any
    bounded context.
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
from src.bootstrap.module_registry import import_task_modules
from src.bootstrap.modules import MODULES
from src.infrastructure.logging.dlq_middleware import DLQMiddleware

logger = structlog.get_logger(__name__)

# 1. Initialise the container and DI integration BEFORE importing tasks.
# This is critical so that DishkaMiddleware is in place when tasks register.
container: AsyncContainer = create_container()
setup_dishka(container=container, broker=broker)

# 1.1 DLQ Middleware: persists failed tasks to the database.
# Uses a dedicated engine to avoid depending on the Dishka request-scoped session.
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

# 2. Now import tasks so they register with the broker.
# Framework-level outbox tasks first (relay + pruner schedules), then
# per-module task modules listed on each manifest.
import src.infrastructure.outbox.tasks  # noqa: F401, E402

import_task_modules(MODULES)


@broker.on_event(TaskiqEvents.WORKER_STARTUP)
async def startup_event(state) -> None:
    """Handle the worker startup lifecycle event.

    Stores the DI container in the worker state so that it can be
    properly closed during shutdown.

    Args:
        state: The TaskIQ worker state object.
    """
    logger.info("TaskIQ Worker started and ready to process tasks")
    # Persist the container in state for graceful shutdown.
    state.dishka_container = container


@broker.on_event(TaskiqEvents.WORKER_SHUTDOWN)
async def shutdown_event(state) -> None:
    """Handle the worker graceful-shutdown lifecycle event.

    Closes the Dishka DI container and releases all managed resources
    (database pools, cache connections, etc.).

    Args:
        state: The TaskIQ worker state object.
    """
    logger.info("Shutting down TaskIQ Worker...")
    if hasattr(state, "dishka_container"):
        await state.dishka_container.close()
        logger.info("Dishka DI container closed successfully")
