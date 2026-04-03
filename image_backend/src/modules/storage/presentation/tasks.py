"""Storage background tasks — image processing and orphan cleanup."""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime, timedelta

from dishka import FromDishka

from src.bootstrap.broker import broker
from src.modules.storage.application.commands.process_image import build_variants
from src.modules.storage.domain.interfaces import IStorageRepository
from src.modules.storage.domain.value_objects import StorageStatus
from src.modules.storage.presentation.sse import SSEManager
from src.shared.interfaces.blob_storage import IBlobStorage
from src.shared.interfaces.config import IStorageConfig
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork
from src.shared.streams import bytes_to_async_stream


@broker.task(
    task_name="process_image",
    queue_name="image_processing",
    retry_on_error=True,
    max_retries=2,
    timeout=300,
)
async def process_image_task(
    storage_object_id: str,
    blob_storage: FromDishka[IBlobStorage],
    storage_repo: FromDishka[IStorageRepository],
    uow: FromDishka[IUnitOfWork],
    config: FromDishka[IStorageConfig],
    sse: FromDishka[SSEManager],
    logger: FromDishka[ILogger],
) -> None:
    """Download raw, process with Pillow, upload variants, update status, push SSE."""
    sid = uuid.UUID(storage_object_id)
    log = logger.bind(storage_object_id=storage_object_id)
    log.info("Processing image started")

    storage_file = await storage_repo.get_by_id(sid)
    if not storage_file:
        log.error("StorageFile not found")
        return

    try:
        # 1. Download raw
        raw_chunks: list[bytes] = []
        async for chunk in blob_storage.download_stream(storage_file.object_key):
            raw_chunks.append(chunk)
        raw_data = b"".join(raw_chunks)
        log.info("Downloaded raw", size=len(raw_data))

        # 2. Process in thread (CPU-bound)
        main_bytes, variants_meta, variants_data = await asyncio.to_thread(
            build_variants, raw_data, sid, config.S3_PUBLIC_BASE_URL
        )

        # 3. Upload main
        main_key = f"public/{sid}.webp"
        await blob_storage.upload_stream(
            main_key, bytes_to_async_stream(main_bytes), "image/webp"
        )

        # 4. Upload variants
        for s3_key, data in variants_data.items():
            await blob_storage.upload_stream(
                s3_key, bytes_to_async_stream(data), "image/webp"
            )

        # 5. Delete raw
        await blob_storage.delete_object(storage_file.object_key)

        # 6. Update DB
        public_url = f"{config.S3_PUBLIC_BASE_URL.rstrip('/')}/{main_key}"
        storage_file.status = StorageStatus.COMPLETED
        storage_file.url = public_url
        storage_file.image_variants = variants_meta
        storage_file.size_bytes = len(main_bytes)
        await storage_repo.update(storage_file)
        await uow.commit()

        # 7. Push SSE
        await sse.publish(
            sid,
            {
                "status": "completed",
                "storage_object_id": str(sid),
                "url": public_url,
                "variants": variants_meta,
            },
        )
        log.info("Processing completed", url=public_url)

    except Exception:
        log.exception("Processing failed")
        storage_file.status = StorageStatus.FAILED
        await storage_repo.update(storage_file)
        await uow.commit()
        await sse.publish(
            sid,
            {
                "status": "failed",
                "storage_object_id": str(sid),
                "error": "Processing failed",
            },
        )
        raise


@broker.task(
    task_name="cleanup_orphans",
    queue_name="maintenance",
    timeout=600,
    schedule=[{"cron": "0 */6 * * *"}],
)
async def cleanup_orphans_task(
    storage_repo: FromDishka[IStorageRepository],
    blob_storage: FromDishka[IBlobStorage],
    uow: FromDishka[IUnitOfWork],
    logger: FromDishka[ILogger],
) -> None:
    """Phase 1: delete PENDING_UPLOAD objects older than 24 hours."""
    log = logger.bind(task="cleanup_orphans")
    cutoff = datetime.now(UTC) - timedelta(hours=24)
    orphans = await storage_repo.list_pending_expired(cutoff)
    log.info("Found orphans", count=len(orphans))

    for orphan in orphans:
        try:
            await blob_storage.delete_object(orphan.object_key)
        except Exception:
            log.warning("Failed to delete S3 object", key=orphan.object_key)
        await storage_repo.mark_as_deleted(orphan.bucket_name, orphan.object_key)

    await uow.commit()
    log.info("Orphan cleanup done", deleted=len(orphans))
