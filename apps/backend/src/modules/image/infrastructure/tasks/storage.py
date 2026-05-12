"""Image module storage tasks — Pillow + S3, no ML.

* ``process_image_task`` — consumes a confirmed upload, downloads raw,
  produces WebP main + variants via Pillow, uploads to S3, marks
  ``status=COMPLETED`` and pushes status via SSE pub/sub.
* ``cleanup_orphans_task`` — six-hourly cron that prunes ``PENDING_UPLOAD``
  rows older than 24 hours.

Both tasks are queued on ``image.processing`` / ``image.maintenance``.
The lean ``apps/workers/image/storage`` worker subscribes to these
queues; the ML inference task lives in :mod:`.rmbg` and is consumed
exclusively by ``apps/workers/image/rmbg`` (separate Railway service
with the torch + transformers + timm + kornia stack installed).
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime, timedelta

import structlog
from dishka.integrations.taskiq import FromDishka, inject

from src.bootstrap.broker import broker
from src.bootstrap.config import Settings
from src.modules.image.domain.events import StorageObjectProcessedEvent
from src.modules.image.domain.interfaces import IBlobStorage, IStorageRepository
from src.modules.image.domain.value_objects import StorageStatus
from src.modules.image.infrastructure.services.image_processor import build_variants
from src.modules.image.infrastructure.services.sse_manager import SSEManager
from src.modules.image.infrastructure.services.streams import bytes_to_async_stream
from src.shared.interfaces.uow import IUnitOfWork

logger = structlog.get_logger(__name__)


@broker.task(
    task_name="process_image",
    queue_name="image.processing",
    retry_on_error=True,
    max_retries=2,
    timeout=300,
)
@inject
async def process_image_task(
    storage_object_id: str,
    blob_storage: FromDishka[IBlobStorage],
    storage_repo: FromDishka[IStorageRepository],
    uow: FromDishka[IUnitOfWork],
    settings: FromDishka[Settings],
    sse: FromDishka[SSEManager],
) -> None:
    """Download raw, run Pillow, upload variants, update DB, push SSE."""
    sid = uuid.UUID(storage_object_id)
    log = logger.bind(storage_object_id=storage_object_id)
    log.info("Processing image started")

    storage_file = await storage_repo.get_by_id(sid)
    if not storage_file:
        log.error("StorageFile not found")
        return

    try:
        raw_chunks: list[bytes] = []
        async for chunk in blob_storage.download_stream(storage_file.object_key):
            raw_chunks.append(chunk)
        raw_data = b"".join(raw_chunks)
        log.info("Downloaded raw", size=len(raw_data))

        main_bytes, variants_meta, variants_data = await asyncio.to_thread(
            build_variants, raw_data, sid, settings.S3_PUBLIC_BASE_URL
        )

        main_key = f"public/{sid}.webp"
        await blob_storage.upload_stream(
            main_key, bytes_to_async_stream(main_bytes), "image/webp"
        )
        for s3_key, data in variants_data.items():
            await blob_storage.upload_stream(
                s3_key, bytes_to_async_stream(data), "image/webp"
            )

        await blob_storage.delete_object(storage_file.object_key)

        public_url = f"{settings.S3_PUBLIC_BASE_URL.rstrip('/')}/{main_key}"
        storage_file.status = StorageStatus.COMPLETED
        storage_file.url = public_url
        storage_file.image_variants = variants_meta
        storage_file.size_bytes = len(main_bytes)
        await storage_repo.update(storage_file)

        # IMG-004 — emit ``StorageObjectProcessedEvent`` so catalog mirrors
        # the new ``url`` / ``image_variants`` into its denormalised
        # ``media_assets`` rows. Critical for the ``/reupload`` flow: same
        # storage_object_id but new processed output — without this event
        # the storefront keeps serving the stale URL.
        storage_file.add_domain_event(
            StorageObjectProcessedEvent(
                storage_object_id=storage_file.id,
                url=public_url,
                image_variants=list(variants_meta),
            )
        )
        uow.register_aggregate(storage_file)
        await uow.commit()

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
    task_name="image_cleanup_orphans",
    queue_name="image.maintenance",
    timeout=600,
    schedule=[{"cron": "0 */6 * * *"}],
)
@inject
async def cleanup_orphans_task(
    storage_repo: FromDishka[IStorageRepository],
    blob_storage: FromDishka[IBlobStorage],
    uow: FromDishka[IUnitOfWork],
) -> None:
    """Delete PENDING_UPLOAD storage objects older than 24 hours."""
    log = logger.bind(task="image_cleanup_orphans")
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
