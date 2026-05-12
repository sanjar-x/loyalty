"""TaskIQ worker entry point — image-storage dedicated.

Subscribes to ``image.processing`` + ``image.maintenance`` queues only.
The ML inference task (``image.ml`` queue) is intentionally NOT
imported, so this bootstrap can run on a lean image (no torch +
transformers + timm + kornia) — those deps live on the
``apps/workers/image/rmbg`` sibling and are absent from
``apps/workers/image/storage``'s pyproject.

Mirrors :mod:`worker_core` but with a narrower task import set. The
initialisation order is identical and load-bearing: container →
``setup_dishka`` → DLQ middleware → tasks. Reordering breaks
``FromDishka[...]`` resolution at runtime.
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

# 2. Import the storage-task submodule by path. We deliberately do NOT
#    import the package (``src.modules.image.infrastructure.tasks``)
#    because that pulls in ``.rmbg``, which would register the ML task
#    on this lean worker's broker and have it subscribe to the
#    ``image.ml`` queue — defeating the split.
import src.modules.image.infrastructure.tasks.storage  # noqa: E402, F401


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
