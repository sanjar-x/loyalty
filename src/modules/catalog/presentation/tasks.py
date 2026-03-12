import structlog
from dishka.integrations.taskiq import FromDishka

from src.bootstrap.taskiq import broker
from src.modules.catalog.application.commands.confirm_brand_logo import (
    ConfirmBrandLogoUploadCommand,
    ConfirmBrandLogoUploadHandler,
)

logger = structlog.get_logger(__name__)


@broker.task(
    queue="catalog_confirm_brand_logo",
    exchange="taskiq_rpc_exchange",
    routing_key="catalog.command.confirm_brand_logo",
)
async def confirm_brand_logo_task(
    payload: dict,
    handler: FromDishka[ConfirmBrandLogoUploadHandler],
) -> dict:
    """
    TaskIQ обработчик для конкретной команды ConfirmBrandLogoUpload.
    """
    logger.info("Начата фоновая обработка команды", command="ConfirmBrandLogoUpload")

    try:
        command = ConfirmBrandLogoUploadCommand(**payload)
        await handler.handle(command)

        logger.info("Команда ConfirmBrandLogoUpload успешно обработана")
        return {"status": "success"}

    except Exception as e:
        logger.error("Сбой при фоновой обработке команды", error=str(e))
        raise
