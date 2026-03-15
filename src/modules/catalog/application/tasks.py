import time
import uuid

from dishka.integrations.taskiq import FromDishka, inject

from src.bootstrap.broker import broker
from src.modules.catalog.application.services.media_processor import BrandLogoProcessor
from src.shared.interfaces.logger import ILogger


@broker.task(
    queue="catalog_process_brand_logo",
    exchange="taskiq_rpc_exchange",
    routing_key="catalog.command.process_brand_logo",
    max_retries=3,
    retry_on_error=True,
)
@inject
async def process_brand_logo_task(
    brand_id: uuid.UUID,
    processor: FromDishka[BrandLogoProcessor],
    logger: FromDishka[ILogger],
) -> dict:
    """
    TaskIQ воркер для обработки (ресайз/WebP) логотипа бренда.
    """
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

        raise
