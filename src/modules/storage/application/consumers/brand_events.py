# src/modules/storage/application/consumers/brand_events.py
"""
Consumer модуля Storage для Integration Events модуля Catalog.

Слушает события из RabbitMQ (через Outbox Relay) и создаёт/обновляет
записи StorageObject в БД модуля Storage.

Все обработчики ИДЕМПОТЕНТНЫ (At-Least-Once гарантия Outbox).
"""

from dishka.integrations.taskiq import FromDishka, inject

from src.bootstrap.broker import broker
from src.bootstrap.config import Settings
from src.modules.storage.domain.interfaces import IStorageRepository
from src.modules.storage.infrastructure.models import StorageObject
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@broker.task(
    queue="storage_brand_events",
    exchange="taskiq_rpc_exchange",
    routing_key="storage.consumers.brand_created",
    max_retries=3,
    retry_on_error=True,
)
@inject
async def handle_brand_created_event(
    brand_id: str,
    object_key: str,
    content_type: str,
    storage_repo: FromDishka[IStorageRepository],
    uow: FromDishka[IUnitOfWork],
    settings: FromDishka[Settings],
    logger: FromDishka[ILogger],
) -> dict:
    """
    Реакция на BrandCreatedEvent: создаёт запись StorageObject.

    Идемпотентность: если запись с таким object_key уже существует,
    пропускаем (дубликат от Outbox Relay).
    """
    log = logger.bind(brand_id=brand_id, object_key=object_key)

    async with uow:
        existing = await storage_repo.get_active_by_key(
            bucket_name=settings.S3_BUCKET_NAME,
            object_key=object_key,
        )
        if existing:
            log.info("StorageObject уже существует, пропуск (идемпотентность)")
            return {"status": "skipped", "reason": "already_exists"}

        storage_obj = StorageObject(
            bucket_name=settings.S3_BUCKET_NAME,
            object_key=object_key,
            content_type=content_type,
            owner_module="catalog",
        )
        await storage_repo.add(storage_obj)
        await uow.commit()

    log.info("StorageObject создан для бренда", file_id=str(storage_obj.id))
    return {"status": "created", "file_id": str(storage_obj.id)}


@broker.task(
    queue="storage_brand_events",
    exchange="taskiq_rpc_exchange",
    routing_key="storage.consumers.brand_logo_processed",
    max_retries=3,
    retry_on_error=True,
)
@inject
async def handle_brand_logo_processed_event(
    brand_id: str,
    object_key: str,
    content_type: str,
    size_bytes: int,
    storage_repo: FromDishka[IStorageRepository],
    uow: FromDishka[IUnitOfWork],
    settings: FromDishka[Settings],
    logger: FromDishka[ILogger],
) -> dict:
    """
    Реакция на BrandLogoProcessedEvent: регистрирует обработанный файл.

    Идемпотентность: если запись с таким object_key уже существует,
    обновляем метаданные (размер, content_type).
    """
    log = logger.bind(brand_id=brand_id, object_key=object_key)

    async with uow:
        existing = await storage_repo.get_active_by_key(
            bucket_name=settings.S3_BUCKET_NAME,
            object_key=object_key,
        )
        if existing:
            existing.size_bytes = size_bytes
            existing.content_type = content_type
            await uow.commit()
            log.info("StorageObject обновлён (идемпотентность)")
            return {"status": "updated", "file_id": str(existing.id)}

        storage_obj = StorageObject(
            bucket_name=settings.S3_BUCKET_NAME,
            object_key=object_key,
            content_type=content_type,
            size_bytes=size_bytes,
            owner_module="catalog",
        )
        await storage_repo.add(storage_obj)
        await uow.commit()

    log.info(
        "StorageObject создан для обработанного логотипа", file_id=str(storage_obj.id)
    )
    return {"status": "created", "file_id": str(storage_obj.id)}
