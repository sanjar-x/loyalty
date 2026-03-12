import structlog
from dishka.async_container import AsyncContainer
from dishka.integrations.taskiq import setup_dishka
from taskiq.events import TaskiqEvents
from taskiq_aio_pika import AioPikaBroker

from src.bootstrap.config import settings
from src.bootstrap.ioc import create_container

logger = structlog.get_logger(__name__)

# Инициализируем настройки

# 1. Настройка брокера TaskIQ
# Создаем выделенный exchange и queue, чтобы отделить фоновые задачи (RPC)
# от доменных событий (Pub/Sub), которые ходят через кастомный RabbitMQPublisher.
broker = AioPikaBroker(
    url=settings.RABBITMQ_URL,  # ty:ignore[unresolved-attribute]
    exchange_name="taskiq_rpc_exchange",
    queue_name="taskiq_background_jobs",
    # Ограничиваем количество одновременно обрабатываемых задач (защита от OOM)
    qos=10,
    # TaskIQ сам поднимет эту часть топологии при старте воркера
    declare_exchange=True,
    declare_queue=True,
).with_middlewares(
    # Здесь можно добавить встроенные мидлвари TaskIQ (например, для метрик или логирования)
)


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
