"""TaskIQ worker entry point — general (everything except image domain).

Pairs with :mod:`src.bootstrap.worker_image_ml` to achieve a clean
domain-based split between the two Railway worker services:

* ``worker``           (this bootstrap) — subscribes to all queues except
                       the image module's (``image_processing``,
                       ``image_maintenance``, ``image_ml``).
* ``image-ml-worker``  (worker_image_ml.py) — subscribes ONLY to the
                       image queues.

The result: zero queue overlap. RabbitMQ delivers each task to the
correct service deterministically — no round-robin contention between a
heavyweight ML worker and a lean outbox/order/payment worker.

Initialization order mirrors :mod:`src.bootstrap.worker` exactly (see
that module's docstring for why ``broker → container → setup_dishka →
import tasks`` is mandatory). The only delta is the
``import_task_modules`` call which receives a filtered ``MODULES`` tuple
with the image module dropped.

``src.bootstrap.worker:broker`` still exists and imports every module —
useful as a single-process fallback for tests / local dev where running
two workers is overkill. Production splits via ``worker_general`` +
``worker_image_ml``.
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

# 2. Framework-level outbox tasks (image-domain-agnostic).
import src.infrastructure.outbox.tasks  # noqa: E402, F401

from src.bootstrap.module_registry import import_task_modules  # noqa: E402
from src.bootstrap.modules import MODULES  # noqa: E402

# 3. Filter out the image module — its tasks are exclusively owned by
#    the ``image-ml-worker`` service (worker_image_ml.py bootstrap).
#    Everything else (outbox handlers, order, payment, logistics, activity,
#    cart, identity, user, referral, supplier, etc.) is registered here.
_GENERAL_MODULES = tuple(m for m in MODULES if m.name != "image")
import_task_modules(_GENERAL_MODULES)


@broker.on_event(TaskiqEvents.WORKER_STARTUP)
async def startup_event(state) -> None:
    """General worker startup hook — stores container in state."""
    logger.info(
        "general TaskIQ Worker started and ready to process tasks",
        registered_modules=[m.name for m in _GENERAL_MODULES],
    )
    state.dishka_container = container


@broker.on_event(TaskiqEvents.WORKER_SHUTDOWN)
async def shutdown_event(state) -> None:
    """General worker shutdown hook — closes Dishka container."""
    logger.info("Shutting down general TaskIQ Worker...")
    if hasattr(state, "dishka_container"):
        await state.dishka_container.close()
        logger.info("Dishka DI container closed successfully")
