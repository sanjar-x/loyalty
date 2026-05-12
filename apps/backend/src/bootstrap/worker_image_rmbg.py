"""TaskIQ worker entry point — image-rmbg dedicated.

Subscribes to the ``image.ml`` queue only — Bria RMBG-2.0 background
removal inference. Pulls in the heavy ML stack via the rmbg task
submodule (torch + transformers + timm + kornia, installed only on
``apps/workers/image/rmbg``).

The storage submodule is also imported so the broker can resolve any
storage-task references that happen to land on this worker as part of
in-process tooling (e.g. RPC fan-out tests); the worker will not
actually subscribe to ``image.processing`` / ``image.maintenance`` at
runtime because TaskIQ queue subscription is queue-name driven, not
task-name driven — DomainSplitBroker routes only the queues this
worker's tasks claim.

Initialisation order matches the other bootstraps: container →
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

# 1.1 DLQ Middleware.
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

# 2. Import the rmbg task — registers ``remove_background`` on the
#    broker when BG_REMOVAL_ENABLED is true. Worker then subscribes to
#    ``image.ml``.
import src.modules.image.infrastructure.tasks.rmbg  # noqa: E402, F401


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
