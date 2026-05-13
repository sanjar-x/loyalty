"""Image-storage worker tasks — Pillow resize + S3, no backend imports.

* ``process_image_task`` — consumes a confirmed upload, downloads raw,
  produces WebP main + variants via Pillow, uploads to S3, updates
  the row, writes the StorageObjectProcessedEvent to the outbox and
  pushes a status frame to Redis Streams.
* ``cleanup_orphans_task`` — six-hourly cron that prunes
  ``PENDING_UPLOAD`` rows older than 24 hours.

Coordination with backend happens through three external surfaces:

* PostgreSQL — the ``storage_objects`` + ``outbox_messages`` tables,
  whose schema is owned by backend's alembic migrations. This worker
  only reads / updates specific columns via raw SQL — no ORM model
  import.
* Redis Streams — channel ``media:status:{uuid}`` (publisher here,
  subscriber in backend's SSE endpoint), wire format = single ``data``
  field carrying a JSON payload.
* RabbitMQ task name ``process_image`` / ``image_cleanup_orphans``
  (publisher = backend's ``broker.kicker()``).

No Python import crosses the boundary.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog
from sqlalchemy import text

from broker import broker
from config import settings
from db import session_factory
from image_processor import build_variants
from publisher import StatusPublisher
from redis_client import redis_client
from s3 import delete_object, download_bytes, upload_bytes

logger = structlog.get_logger(__name__)


# Status values match what backend writes (StorageStatus enum mirrored
# at the wire level). Worker never imports the enum class — keeps the
# string contract local.
_STATUS_COMPLETED = "COMPLETED"
_STATUS_FAILED = "FAILED"
_STATUS_PENDING_UPLOAD = "PENDING_UPLOAD"
_STATUS_DELETED = "DELETED"

# Outbox event metadata — must match what backend's relay dispatcher
# registry recognises. The relay matches on ``event_type`` to dispatch
# to the right consumer task (catalog mirrors processed URLs into its
# denormalised ``media_assets`` rows).
_AGGREGATE_TYPE = "StorageObject"
_EVENT_TYPE_PROCESSED = "StorageObjectProcessedEvent"


async def _fetch_storage_object(
    sid: uuid.UUID,
) -> tuple[str, str] | None:
    """Return ``(object_key, bucket_name)`` for ``sid`` or ``None``."""
    async with session_factory() as session:
        result = await session.execute(
            text(
                "SELECT object_key, bucket_name "
                "FROM storage_objects WHERE id = :id"
            ),
            {"id": sid},
        )
        row = result.first()
        return (row.object_key, row.bucket_name) if row else None


async def _mark_completed(
    sid: uuid.UUID,
    public_url: str,
    variants_meta: list[dict[str, Any]],
    main_size_bytes: int,
) -> None:
    """Update the row to COMPLETED and append the processed event in
    the same transaction so the outbox relay sees both atomically.
    """
    payload = {
        "storage_object_id": str(sid),
        "url": public_url,
        "image_variants": variants_meta,
    }
    async with session_factory() as session, session.begin():
        await session.execute(
            text(
                "UPDATE storage_objects "
                "SET status = :status, url = :url, "
                "    image_variants = :variants::jsonb, "
                "    size_bytes = :size "
                "WHERE id = :id"
            ),
            {
                "id": sid,
                "status": _STATUS_COMPLETED,
                "url": public_url,
                "variants": json.dumps(variants_meta),
                "size": main_size_bytes,
            },
        )
        await session.execute(
            text(
                "INSERT INTO outbox_messages "
                "(id, aggregate_type, aggregate_id, event_type, payload, created_at) "
                "VALUES "
                "(:id, :agg_type, :agg_id, :event_type, :payload::jsonb, NOW())"
            ),
            {
                "id": uuid.uuid4(),
                "agg_type": _AGGREGATE_TYPE,
                "agg_id": str(sid),
                "event_type": _EVENT_TYPE_PROCESSED,
                "payload": json.dumps(payload),
            },
        )


async def _mark_failed(sid: uuid.UUID) -> None:
    """Flip the row to FAILED. No outbox row — failure is surfaced via
    the SSE channel only; downstream consumers don't react to it.
    """
    async with session_factory() as session, session.begin():
        await session.execute(
            text(
                "UPDATE storage_objects SET status = :status WHERE id = :id"
            ),
            {"id": sid, "status": _STATUS_FAILED},
        )


@broker.task(
    task_name="process_image",
    queue_name="image.processing",
    retry_on_error=True,
    max_retries=2,
    timeout=300,
)
async def process_image_task(storage_object_id: str) -> None:
    """Download raw, run Pillow, upload variants, update DB, push status."""
    sid = uuid.UUID(storage_object_id)
    log = logger.bind(storage_object_id=storage_object_id)
    log.info("Processing image started")
    publisher = StatusPublisher(redis_client)

    fetched = await _fetch_storage_object(sid)
    if fetched is None:
        log.error("StorageFile not found")
        return
    object_key, _bucket_name = fetched

    try:
        raw_data = await download_bytes(object_key)
        log.info("Downloaded raw", size=len(raw_data))

        main_bytes, variants_meta, variants_data = await asyncio.to_thread(
            build_variants, raw_data, sid, settings.S3_PUBLIC_BASE_URL
        )

        main_key = f"public/{sid}.webp"
        await upload_bytes(main_key, main_bytes, "image/webp")
        for s3_key, data in variants_data.items():
            await upload_bytes(s3_key, data, "image/webp")

        await delete_object(object_key)

        public_url = f"{settings.S3_PUBLIC_BASE_URL.rstrip('/')}/{main_key}"
        await _mark_completed(sid, public_url, variants_meta, len(main_bytes))

        await publisher.publish(
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
        await _mark_failed(sid)
        await publisher.publish(
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
async def cleanup_orphans_task() -> None:
    """Delete PENDING_UPLOAD storage objects older than 24 hours."""
    log = logger.bind(task="image_cleanup_orphans")
    cutoff = datetime.now(UTC) - timedelta(hours=24)

    async with session_factory() as session:
        result = await session.execute(
            text(
                "SELECT id, object_key, bucket_name FROM storage_objects "
                "WHERE status = :status AND created_at < :cutoff"
            ),
            {"status": _STATUS_PENDING_UPLOAD, "cutoff": cutoff},
        )
        orphans = list(result.all())

    log.info("Found orphans", count=len(orphans))

    for orphan in orphans:
        try:
            await delete_object(orphan.object_key)
        except Exception:
            log.warning(
                "Failed to delete S3 object", key=orphan.object_key
            )
        async with session_factory() as session, session.begin():
            await session.execute(
                text(
                    "UPDATE storage_objects SET status = :status "
                    "WHERE id = :id"
                ),
                {"id": orphan.id, "status": _STATUS_DELETED},
            )

    log.info("Orphan cleanup done", deleted=len(orphans))
