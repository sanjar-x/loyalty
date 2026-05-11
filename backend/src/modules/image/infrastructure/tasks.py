"""Image module background tasks.

* ``process_image_task`` — consumes a confirmed upload, downloads raw,
  produces WebP main + variants via Pillow, uploads to S3, marks
  ``status=COMPLETED`` and pushes status via SSE pub/sub.
* ``cleanup_orphans_task`` — daily-ish cron that prunes
  ``PENDING_UPLOAD`` rows older than 24 hours.

Wired into TaskIQ via :data:`broker`. Imported from the image module's
manifest (``module.py``) so the worker / scheduler picks them up
through the standard ``import_task_modules`` registry.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime, timedelta

import structlog
from dishka.integrations.taskiq import FromDishka, inject

from src.bootstrap.broker import broker
from src.bootstrap.config import Settings, settings
from src.modules.image.domain.events import (
    BackgroundRemovedEvent,
    StorageObjectProcessedEvent,
)
from src.modules.image.domain.interfaces import (
    IBackgroundRemover,
    IBlobStorage,
    IStorageRepository,
)
from src.modules.image.domain.value_objects import DerivationKind, StorageStatus
from src.modules.image.infrastructure.services.image_processor import build_variants
from src.modules.image.infrastructure.services.sse_manager import SSEManager
from src.modules.image.infrastructure.services.streams import bytes_to_async_stream
from src.shared.interfaces.uow import IUnitOfWork

logger = structlog.get_logger(__name__)


@broker.task(
    task_name="process_image",
    queue_name="image_processing",
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

        # IMG-004 — emit ``StorageObjectProcessedEvent`` so catalog
        # mirrors the new ``url`` / ``image_variants`` into its
        # denormalised ``media_assets`` rows. Critical for the
        # ``/reupload`` flow: same storage_object_id but new processed
        # output — without this event the storefront keeps serving the
        # stale URL.
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
    queue_name="image_maintenance",
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


# ---------------------------------------------------------------------------
# IMG-007 — background removal (Bria RMBG-2.0) on a separate ML queue
# ---------------------------------------------------------------------------
#
# Conditional registration: only the dedicated ``image-ml-worker`` Railway
# service (BG_REMOVAL_ENABLED=true + [bg-removal] extras installed +
# Bria RMBG-2.0 model on a persistent volume) subscribes to the
# ``image_ml`` queue. General workers (web / worker / scheduler with
# BG_REMOVAL_ENABLED=false) do NOT register this task and therefore are
# NOT round-robin consumers of the queue — eliminating the race where a
# lean worker would pick up an ML task and serve a 503 via
# NoopBackgroundRemover.
#
# Implementation note: we keep the function body at module level (regular
# ``async def``) so its indentation stays sane, then rebind the name to
# the broker-decorated task only when the flag is on. The else-branch is
# a no-op: the bare coroutine remains importable but is NOT registered
# with the broker and therefore the worker never subscribes to the
# ``image_ml`` queue.


async def remove_background_task(
    derived_storage_object_id: str,
    blob_storage: FromDishka[IBlobStorage],
    storage_repo: FromDishka[IStorageRepository],
    uow: FromDishka[IUnitOfWork],
    settings: FromDishka[Settings],
    sse: FromDishka[SSEManager],
    bg_remover: FromDishka[IBackgroundRemover],
) -> None:
    """Run the ML cutout for a pre-provisioned derivation row.

    The ``RequestBackgroundRemovalHandler`` already inserted the
    PROCESSING placeholder so the SSE channel is addressable from the
    moment the HTTP 202 response left the API. This task fills in the
    real ``object_key`` / ``url`` / ``image_variants`` and pushes the
    completion / failure event.

    Run on a dedicated queue (``image_ml``) so the regular
    ``image_processing`` workers stay free of the ~1.6 GB model
    footprint. The matching Railway worker installs the optional
    ``[bg-removal]`` extra; web / generic workers do not.
    """
    sid = uuid.UUID(derived_storage_object_id)
    log = logger.bind(derived_storage_object_id=derived_storage_object_id)
    log.info("background_removal_started")

    derived = await storage_repo.get_by_id(sid)
    if derived is None or derived.parent_storage_object_id is None:
        log.error("derived_storage_object_missing_or_not_a_derivation")
        return

    parent_id = derived.parent_storage_object_id
    parent = await storage_repo.get_by_id(parent_id)
    if parent is None:
        log.error("parent_storage_object_missing")
        derived.status = StorageStatus.FAILED
        await storage_repo.update(derived)
        await uow.commit()
        return

    try:
        # Pull the *processed* parent bytes — that's the public WebP
        # the storefront already serves, so the cutout always runs
        # against the same pixels the customer will see.
        processed_key = f"public/{parent_id}.webp"
        raw_chunks: list[bytes] = []
        async for chunk in blob_storage.download_stream(processed_key):
            raw_chunks.append(chunk)
        parent_bytes = b"".join(raw_chunks)
        log.info("parent_bytes_fetched", size=len(parent_bytes))

        cutout_bytes = await bg_remover.remove(parent_bytes)
        log.info("inference_done", cutout_size=len(cutout_bytes))

        cutout_key = f"public/{sid}_bg_removed.webp"
        await blob_storage.upload_stream(
            cutout_key,
            bytes_to_async_stream(cutout_bytes),
            bg_remover.output_content_type,
        )

        # Drop the placeholder — the real key replaces it. We don't
        # delete the placeholder from S3 because no upload was ever
        # made for it (it's just a DB-side string).

        public_url = f"{settings.S3_PUBLIC_BASE_URL.rstrip('/')}/{cutout_key}"
        derived.status = StorageStatus.COMPLETED
        derived.object_key = cutout_key
        derived.url = public_url
        derived.size_bytes = len(cutout_bytes)
        derived.content_type = bg_remover.output_content_type
        # No variants for the cutout in this iteration. The downstream
        # ``compute_media_diff`` flow accepts an empty list — variant
        # generation can layer on top later if needed.
        derived.image_variants = []
        await storage_repo.update(derived)

        derived.add_domain_event(
            BackgroundRemovedEvent(
                storage_object_id=derived.id,
                parent_storage_object_id=parent_id,
                url=public_url,
                derivation_kind=DerivationKind.BG_REMOVED.value,
                image_variants=[],
            )
        )
        uow.register_aggregate(derived)
        await uow.commit()

        await sse.publish(
            sid,
            {
                "status": "completed",
                "storage_object_id": str(sid),
                "url": public_url,
                "variants": [],
                "kind": DerivationKind.BG_REMOVED.value,
            },
        )
        log.info("background_removal_completed", url=public_url)

    except Exception:
        log.exception("background_removal_failed")
        derived.status = StorageStatus.FAILED
        await storage_repo.update(derived)
        await uow.commit()
        await sse.publish(
            sid,
            {
                "status": "failed",
                "storage_object_id": str(sid),
                "error": "Background removal failed",
                "kind": DerivationKind.BG_REMOVED.value,
            },
        )
        raise


# IMG-007 — conditional registration. See the long comment above the
# function for the rationale. The rebind below converts the bare
# ``remove_background_task`` coroutine into a TaskIQ-registered task
# only on the dedicated ``image-ml-worker`` service.
if settings.BG_REMOVAL_ENABLED:
    remove_background_task = broker.task(
        task_name="remove_background",
        queue_name="image_ml",
        retry_on_error=True,
        max_retries=2,
        timeout=240,
    )(inject(remove_background_task))
