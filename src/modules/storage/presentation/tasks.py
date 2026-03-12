# src/modules/storage/presentation/tasks.py
import structlog

from src.bootstrap.taskiq import broker

logger = structlog.get_logger(__name__)


@broker.task(task_name="storage.process_image")
async def process_image_task(file_id: str) -> None:
    """
    Пример Background: RPC Task для обработки загруженного изображения.
    """
    logger.info("Обработка фоновой задачи: storage.process_image", file_id=file_id)
