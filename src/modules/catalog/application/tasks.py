import time
import uuid

import structlog
from dishka.integrations.taskiq import FromDishka, inject

from src.bootstrap.broker import broker
from src.modules.catalog.application.services.media_processor import BrandLogoProcessor

logger = structlog.get_logger(__name__)


@broker.task(
    queue="catalog_process_brand_logo",
    exchange="taskiq_rpc_exchange",
    routing_key="catalog.command.process_brand_logo",
)
@inject
async def process_brand_logo_task(
    brand_id: uuid.UUID,
    processor: FromDishka[BrandLogoProcessor],
) -> dict:
    """
    TaskIQ воркер для обработки (ресайз/WebP) логотипа бренда.
    """
    # Привязываем контекст задачи к логгеру, чтобы не передавать brand_id вручную в каждый вызов
    log = logger.bind(task="process_brand_logo", brand_id=str(brand_id))

    log.info("Воркер принял задачу в обработку")
    start_time = time.perf_counter()

    try:
        # Передаем выполнение в доменный сервис
        await processor.process(brand_id=brand_id)

        execution_time = time.perf_counter() - start_time
        log.info("Задача успешно завершена", duration_sec=round(execution_time, 3))

        return {"status": "success", "brand_id": str(brand_id)}

    except Exception as e:
        execution_time = time.perf_counter() - start_time
        # exception() автоматически запишет stack trace
        log.exception(
            "Критическая ошибка выполнения задачи",
            error_type=type(e).__name__,
            duration_sec=round(execution_time, 3),
        )

        # Мы возвращаем ошибку в словаре для RPC, но TaskIQ также увидит исключение
        return {"status": "error", "message": str(e), "brand_id": str(brand_id)}
