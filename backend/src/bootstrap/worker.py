"""TaskIQ worker entry point.

IMPORTANT: The initialisation order in this module is critical and must
not be changed.

Dependency graph at worker startup:
    1. ``broker``        -- created in ``src/bootstrap/broker.py`` (imported above).
    2. ``container``     -- Dishka DI container (``create_container()``).
    3. ``setup_dishka()``-- registers ``DishkaMiddleware`` on the broker.
    4. ``import tasks``  -- tasks register themselves via the ``@broker.task()``
       decorator.

Why this exact order?
    ``@broker.task()`` calls ``broker.register_task()`` at import time.
    ``DishkaMiddleware`` must already be attached to the broker at that
    point; otherwise ``FromDishka[...]`` dependencies will not resolve at
    execution time and the worker will crash with a runtime error.

What breaks if the order is violated:
    - Moving task imports above ``setup_dishka()``: tasks register without
      the middleware, leading to ``AttributeError`` / ``KeyError`` at
      execution time.
    - Removing the ``# noqa`` markers and letting isort / ruff ``--fix``
      hoist the task imports to the top: same problem.

Auto-formatter protection:
    Task imports are annotated with ``# noqa`` to suppress E402 (module-
    level import not at top of file).  Do NOT remove these markers during
    code cleanup.
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
import src.infrastructure.outbox.tasks  # noqa
import src.modules.catalog.application.tasks  # noqa
import src.modules.storage.application.consumers.brand_events  # noqa
import src.modules.storage.presentation.tasks  # noqa
import src.modules.identity.application.consumers.role_events  # noqa
import src.modules.user.application.consumers.identity_events  # noqa


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
