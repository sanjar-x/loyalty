import structlog
from dishka.async_container import AsyncContainer
from dishka.integrations.taskiq import setup_dishka
from taskiq.events import TaskiqEvents

# Обязательно импортируем все файлы tasks.py, чтобы декораторы @broker.task отработали
from src.bootstrap.ioc import create_container
from src.bootstrap.taskiq import broker

logger = structlog.get_logger(__name__)


# 2. Интеграция с IoC (Dishka)
@broker.on_event(TaskiqEvents.WORKER_STARTUP)
async def startup_event(state) -> None:
    """
    Хук жизненного цикла воркера. Вызывается при старте процесса `taskiq worker`.
    """
    logger.info("Инициализация TaskIQ Worker'а...")

    # Собираем тот же самый DI-контейнер, что и для FastAPI.
    # Воркер получит доступ к базам данных, кэшу и репозиториям.
    container: AsyncContainer = create_container()

    # Интегрируем Dishka с брокером.
    # Это добавит middleware, которое будет открывать Scope.REQUEST
    # при старте КАЖДОЙ задачи и закрывать его при завершении.
    setup_dishka(container=container, broker=broker)

    logger.info("DI-контейнер Dishka успешно интегрирован в TaskIQ")


@broker.on_event(TaskiqEvents.CLIENT_SHUTDOWN)
async def shutdown_event(state) -> None:
    """
    Graceful shutdown воркера.
    """
    logger.info("Остановка TaskIQ Worker'а...")
    if hasattr(state, "dishka_container"):
        await state.dishka_container.close()
        logger.info("DI-контейнер Dishka успешно закрыт")
