# src/bootstrap/worker.py
import structlog
from dishka.async_container import AsyncContainer
from dishka.integrations.taskiq import setup_dishka
from taskiq.events import TaskiqEvents

from src.bootstrap.broker import broker
from src.bootstrap.container import create_container

logger = structlog.get_logger(__name__)

# 1. Инициализируем контейнер и интеграцию ДО импорта задач.
# Это критично, чтобы DishkaMiddleware успел подхватить задачи при их регистрации.
container: AsyncContainer = create_container()
setup_dishka(container=container, broker=broker)

# 2. Теперь импортируем задачи.
import src.modules.catalog.application.tasks  # noqa
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
