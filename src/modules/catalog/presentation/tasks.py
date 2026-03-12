# src/modules/catalog/presentation/tasks.py
import structlog
from dishka import AsyncContainer
from dishka.integrations.taskiq import FromDishka

from src.bootstrap.taskiq import broker
from src.modules.catalog.application.commands.confirm_brand_logo import (
    ConfirmBrandLogoUploadCommand,
    ConfirmBrandLogoUploadHandler,
)

logger = structlog.get_logger(__name__)


@broker.task(
    queue="taskiq_background_jobs",
    exchange="taskiq_rpc_exchange",
    routing_key="catalog.command.process",
)
async def process_catalog_command(
    command_type: str,
    payload: dict,
    container: FromDishka[AsyncContainer],
) -> dict:
    """
    Универсальный TaskIQ обработчик команд для модуля Catalog.
    Извлекает подходящий CommandHandler из DI-контейнера и делегирует ему работу.
    """
    logger.info(
        "Начата фоновая обработка команды",
        command_type=command_type,
        payload=payload,
    )

    try:
        if command_type == "ConfirmBrandLogoUploadCommand":
            handler = await container.get(ConfirmBrandLogoUploadHandler)
            command = ConfirmBrandLogoUploadCommand(**payload)
            await handler.handle(command)
            logger.info("Команда успешно обработана", command_type=command_type)
            return {"status": "success", "command_type": command_type}

        else:
            logger.error("Неизвестный тип команды", command_type=command_type)
            return {"status": "error", "reason": "Unknown command_type"}

    except Exception as e:
        logger.error(
            "Сбой при фоновой обработке команды",
            command_type=command_type,
            error=str(e),
        )
        raise
