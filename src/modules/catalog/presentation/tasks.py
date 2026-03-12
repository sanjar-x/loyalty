import uuid

import structlog
from dishka.integrations.taskiq import FromDishka

from src.bootstrap.taskiq import broker
from src.modules.catalog.application.services.media_processor import BrandLogoProcessor

logger = structlog.get_logger(__name__)


@broker.task(
    queue="catalog_process_brand_logo",
    exchange="taskiq_rpc_exchange",
    routing_key="catalog.command.process_brand_logo",
)
async def process_brand_logo_task(
    brand_id: uuid.UUID,
    raw_object_key: str,
    processor: FromDishka[BrandLogoProcessor],
) -> dict:
    """
    TaskIQ воркер для обработки (ресайз/WebP) логотипа бренда.
    """
    logger.info("Начата обработка логотипа", brand_id=str(brand_id))

    try:
        await processor.process(brand_id=brand_id, raw_object_key=raw_object_key)
        return {"status": "success"}
    except Exception as e:
        logger.exception(
            "Критическая ошибка при процессинге логотипа", brand_id=str(brand_id)
        )
        return {"status": "error", "message": str(e)}
