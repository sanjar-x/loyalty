"""TaskIQ worker entry point.

IMPORTANT: The initialisation order in this module is critical and must
not be changed.  See the original docstring for the dependency graph.
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

# 2. Now import tasks so they register with the broker.
import src.modules.storage.presentation.tasks  # noqa: E402, F401


@broker.on_event(TaskiqEvents.WORKER_STARTUP)
async def startup_event(state) -> None:
    """Handle the worker startup lifecycle event."""
    logger.info("TaskIQ Worker started and ready to process tasks")
    state.dishka_container = container


@broker.on_event(TaskiqEvents.WORKER_SHUTDOWN)
async def shutdown_event(state) -> None:
    """Handle the worker graceful-shutdown lifecycle event."""
    logger.info("Shutting down TaskIQ Worker...")
    if hasattr(state, "dishka_container"):
        await state.dishka_container.close()
        logger.info("Dishka DI container closed successfully")
