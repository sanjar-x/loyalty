"""Consumer handlers for Catalog module integration events.

Listens to events published via the Outbox Relay through RabbitMQ and
creates or updates ``StorageFile`` records in the Storage module's
database.

All handlers are **idempotent** to support at-least-once delivery
guarantees provided by the Outbox pattern.
"""

from dishka.integrations.taskiq import FromDishka, inject

from src.bootstrap.broker import broker
from src.modules.storage.domain.entities import StorageFile
from src.modules.storage.domain.interfaces import IStorageRepository
from src.shared.interfaces.config import IStorageConfig
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@broker.task(
    queue="storage_brand_events",
    exchange="taskiq_rpc_exchange",
    routing_key="storage.consumers.brand_created",
    max_retries=3,
    retry_on_error=True,
    timeout=30,  # 30 seconds: lightweight DB operation
)
@inject
async def handle_brand_created_event(
    brand_id: str,
    object_key: str,
    content_type: str,
    storage_repo: FromDishka[IStorageRepository],
    uow: FromDishka[IUnitOfWork],
    settings: FromDishka[IStorageConfig],
    logger: FromDishka[ILogger],
) -> dict:
    """Handle a ``BrandCreatedEvent`` by creating a ``StorageFile`` record.

    Idempotency: if a record with the given ``object_key`` already exists
    the handler skips creation (duplicate delivery from Outbox Relay).

    Args:
        brand_id: Identifier of the newly created brand.
        object_key: S3 object key associated with the brand.
        content_type: MIME type of the uploaded file.
        storage_repo: Storage repository for file metadata persistence.
        uow: Unit of Work for transactional consistency.
        settings: Storage configuration (bucket name, etc.).
        logger: Structured logger instance.

    Returns:
        A dict with ``status`` indicating ``"created"`` or ``"skipped"``.
    """
    log = logger.bind(brand_id=brand_id, object_key=object_key)

    async with uow:
        existing = await storage_repo.get_active_by_key(
            bucket_name=settings.S3_BUCKET_NAME,
            object_key=object_key,
        )
        if existing:
            log.info("StorageFile already exists, skipping (idempotency)")
            return {"status": "skipped", "reason": "already_exists"}

        storage_file = StorageFile.create(
            bucket_name=settings.S3_BUCKET_NAME,
            object_key=object_key,
            content_type=content_type,
            owner_module="catalog",
        )
        await storage_repo.add(storage_file)
        await uow.commit()

    log.info("StorageFile created for brand", file_id=str(storage_file.id))
    return {"status": "created", "file_id": str(storage_file.id)}


@broker.task(
    queue="storage_brand_events",
    exchange="taskiq_rpc_exchange",
    routing_key="storage.consumers.brand_logo_processed",
    max_retries=3,
    retry_on_error=True,
    timeout=30,  # 30 seconds: lightweight DB operation
)
@inject
async def handle_brand_logo_processed_event(
    brand_id: str,
    object_key: str,
    content_type: str,
    size_bytes: int,
    storage_repo: FromDishka[IStorageRepository],
    uow: FromDishka[IUnitOfWork],
    settings: FromDishka[IStorageConfig],
    logger: FromDishka[ILogger],
) -> dict:
    """Handle a ``BrandLogoProcessedEvent`` by registering the processed file.

    Idempotency: if a record with the given ``object_key`` already exists
    the handler updates its metadata (size, content type) instead of
    creating a duplicate.

    Args:
        brand_id: Identifier of the brand whose logo was processed.
        object_key: S3 object key of the processed logo.
        content_type: MIME type of the processed file.
        size_bytes: Size of the processed file in bytes.
        storage_repo: Storage repository for file metadata persistence.
        uow: Unit of Work for transactional consistency.
        settings: Storage configuration (bucket name, etc.).
        logger: Structured logger instance.

    Returns:
        A dict with ``status`` indicating ``"created"`` or ``"updated"``.
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
            await storage_repo.update(existing)
            await uow.commit()
            log.info("StorageFile updated (idempotency)")
            return {"status": "updated", "file_id": str(existing.id)}

        storage_file = StorageFile.create(
            bucket_name=settings.S3_BUCKET_NAME,
            object_key=object_key,
            content_type=content_type,
            size_bytes=size_bytes,
            owner_module="catalog",
        )
        await storage_repo.add(storage_file)
        await uow.commit()

    log.info("StorageFile created for processed logo", file_id=str(storage_file.id))
    return {"status": "created", "file_id": str(storage_file.id)}
