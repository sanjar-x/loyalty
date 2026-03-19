"""
Catalog background tasks (TaskIQ workers).

Defines asynchronous workers for CPU/IO-bound operations that should
not block the HTTP request cycle (e.g. logo image processing).
Part of the application layer.
"""

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
    timeout=300,  # 5 min — covers download + convert + upload
)
@inject
async def process_brand_logo_task(
    brand_id: uuid.UUID,
    processor: FromDishka[BrandLogoProcessor],
    logger: FromDishka[ILogger],
) -> dict:
    """Download a raw brand logo, convert to WebP, and upload the result.

    Runs as a background TaskIQ job triggered by ``BrandLogoConfirmedEvent``.
    On success, transitions the Brand's logo FSM to COMPLETED.
    On failure (after retries), transitions to FAILED.

    Args:
        brand_id: UUID of the brand whose logo should be processed.
        processor: Injected ``BrandLogoProcessor`` service.
        logger: Injected structured logger.

    Returns:
        Dict with ``status`` and ``brand_id`` on success.
    """
    log = logger.bind(task="process_brand_logo", brand_id=str(brand_id))

    log.info("Worker accepted brand logo processing task")
    start_time = time.perf_counter()

    try:
        await processor.process(brand_id=brand_id)

        execution_time = time.perf_counter() - start_time
        log.info("Task completed successfully", duration_sec=round(execution_time, 3))

        return {"status": "success", "brand_id": str(brand_id)}

    except Exception as e:
        execution_time = time.perf_counter() - start_time
        log.exception(
            "Critical task execution error",
            error_type=type(e).__name__,
            duration_sec=round(execution_time, 3),
        )

        raise
