# src/bootstrap/worker.py
"""
Точка входа TaskIQ-воркера.

ВАЖНО: Порядок инициализации в этом модуле критичен и не должен меняться.

Схема зависимостей при старте воркера:
    1. broker          — создаётся в src/bootstrap/broker.py (импортируется вверху)
    2. container       — DI-контейнер Dishka (create_container())
    3. setup_dishka()  — регистрирует DishkaMiddleware на брокере
    4. import tasks    — задачи регистрируются через @broker.task() декоратор

Почему именно такой порядок?
    @broker.task() при импорте немедленно вызывает broker.register_task().
    DishkaMiddleware должна быть уже установлена на брокере в этот момент,
    иначе зависимости (FromDishka[...]) не будут разрешаться при выполнении задач,
    и воркер упадёт с ошибкой в runtime при первом же вызове.

Что сломается при нарушении порядка:
    - Если переместить импорты tasks выше setup_dishka():
      задачи зарегистрируются без middleware → AttributeError/KeyError при выполнении.
    - Если убрать # noqa: E402 и запустить isort/ruff --fix:
      автоформаттер поднимет импорты tasks наверх → та же проблема.

Защита от автоформаттеров:
    Импорты задач помечены # noqa для подавления E402 (import not at top of file).
    Директива type: ignore[import] добавлена там, где задачи не экспортируют API.
    Не удалять эти комментарии при «чистке» кода.
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

# 1. Инициализируем контейнер и интеграцию ДО импорта задач.
# Это критично, чтобы DishkaMiddleware успел подхватить задачи при их регистрации.
container: AsyncContainer = create_container()
setup_dishka(container=container, broker=broker)

# 1.1 DLQ Middleware: сохраняет проваленные задачи в БД.
# Используем отдельный engine, чтобы не зависеть от Dishka request-scoped session.
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

# 2. Теперь импортируем задачи.
import src.infrastructure.outbox.tasks  # noqa
import src.modules.catalog.application.tasks  # noqa
import src.modules.storage.application.consumers.brand_events  # noqa
import src.modules.storage.presentation.tasks  # noqa


@broker.on_event(TaskiqEvents.WORKER_STARTUP)
async def startup_event(state) -> None:
    """
    Хук жизненного цикла воркера.
    """
    logger.info("TaskIQ Worker запущен и готов к работе")
    # Сохраняем контейнер в State для корректного закрытия
    state.dishka_container = container


@broker.on_event(TaskiqEvents.WORKER_SHUTDOWN)
async def shutdown_event(state) -> None:
    """
    Graceful shutdown воркера.
    """
    logger.info("Остановка TaskIQ Worker'а...")
    if hasattr(state, "dishka_container"):
        await state.dishka_container.close()
        logger.info("DI-контейнер Dishka успешно закрыт")
