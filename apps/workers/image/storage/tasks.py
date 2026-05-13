"""Image-storage worker tasks — Pillow resize + S3, no backend imports.

* ``image_process_task`` — consumes a confirmed upload, downloads raw,
  produces WebP main + variants via Pillow, uploads to S3, updates
  the row, writes the StorageObjectProcessedEvent to the outbox and
  pushes a status frame to Redis Streams.
* ``image_cleanup_orphans_task`` — six-hourly cron that prunes
  ``PENDING_UPLOAD`` rows older than 24 hours.

Coordination with backend happens through three external surfaces:

* PostgreSQL — the ``storage_objects`` + ``outbox_messages`` tables,
  whose schema is owned by backend's alembic migrations. This worker
  only reads / updates specific columns via raw SQL — no ORM model
  import.
* Redis Streams — channel ``media:status:{uuid}`` (publisher here,
  subscriber in backend's SSE endpoint), wire format = single ``data``
  field carrying a JSON payload.
* RabbitMQ task names ``image_process`` / ``image_cleanup_orphans``
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
from broker import broker
from config import settings
from db import session_factory
from image_processor import build_variants
from PIL import UnidentifiedImageError
from PIL.Image import DecompressionBombError
from publisher import StatusPublisher
from redis_client import redis_client
from s3 import delete_object, download_bytes, upload_bytes
from sqlalchemy import text

# Errors we know we cannot recover from by retrying — they originate
# from the uploaded bytes themselves (corrupted file, decompression
# bomb, unrecognised format). Retrying the same payload will fail the
# same way, so we mark FAILED and skip the TaskIQ retry path. Anything
# else (S3 timeout, Redis connection blip, asyncpg disconnect) is
# treated as transient and re-raised so the broker will retry.
_TERMINAL_PROCESSING_ERRORS: tuple[type[BaseException], ...] = (
    UnidentifiedImageError,
    DecompressionBombError,
    ValueError,
)

logger = structlog.get_logger(__name__)


# Status values match what backend writes (StorageStatus enum mirrored
# at the wire level). Worker never imports the enum class — keeps the
# string contract local.
_STATUS_COMPLETED = "COMPLETED"
_STATUS_FAILED = "FAILED"
_STATUS_PENDING_UPLOAD = "PENDING_UPLOAD"
_STATUS_DELETED = "DELETED"

# Outbox event metadata — must match what backend writes via
# :class:`ImageEvent` (see ``apps/backend/src/modules/image/domain/events.py``).
# Relay's dispatcher matches on ``event_type`` to fan out to subscribers
# (catalog mirrors processed URLs into its denormalised ``media_assets``
# rows on ``StorageObjectProcessedEvent``); ``aggregate_type`` is the
# bounded-context label and must stay aligned with backend's events so
# operators reading the outbox table see one consistent value.
_AGGREGATE_TYPE = "image"
_EVENT_TYPE_PROCESSED = "StorageObjectProcessedEvent"

# Progress stages emitted between ``status: processing`` start and the
# terminal ``status: completed`` / ``status: failed`` frames. Stage
# names are part of the wire contract with the SSE subscriber — adding
# or renaming one is a breaking change.
_PROGRESS_STAGE_STARTED = "started"
_PROGRESS_STAGE_DOWNLOADED = "downloaded"
_PROGRESS_STAGE_VARIANTS_BUILT = "variants_built"
_PROGRESS_STAGE_UPLOADED = "uploaded"


async def _fetch_storage_object(
    sid: uuid.UUID,
) -> tuple[str, str] | None:
    """Return ``(object_key, bucket_name)`` for ``sid`` or ``None``."""
    async with session_factory() as session:
        result = await session.execute(
            text("SELECT object_key, bucket_name FROM storage_objects WHERE id = :id"),
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
                # ``CAST(:variants AS jsonb)`` instead of ``:variants::jsonb``
                # because SQLAlchemy's ``text()`` bind-param parser fails on
                # ``:name::cast`` — it treats the trailing ``::`` as a cast
                # operator AFTER consuming ``:name``, leaving the placeholder
                # untranslated. PG then sees a literal ``:variants`` and
                # raises ``syntax error at or near \":\"``.
                "UPDATE storage_objects "
                "SET status = :status, url = :url, "
                "    image_variants = CAST(:variants AS jsonb), "
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
                # ``CAST(:payload AS jsonb)`` instead of ``:payload::jsonb``
                # for the same reason as the UPDATE above.
                "INSERT INTO outbox_messages "
                "(id, aggregate_type, aggregate_id, event_type, payload, created_at) "
                "VALUES "
                "(:id, :agg_type, :agg_id, :event_type, CAST(:payload AS jsonb), NOW())"
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
            text("UPDATE storage_objects SET status = :status WHERE id = :id"),
            {"id": sid, "status": _STATUS_FAILED},
        )


async def _mark_failed_safe(sid: uuid.UUID, log: structlog.stdlib.BoundLogger) -> None:
    """Best-effort wrapper around :func:`_mark_failed`.

    The caller is already on the failure path — we don't want a second
    error (e.g. a Postgres connection drop while flipping status) to
    suppress the failure SSE frame the user is waiting for. Swallow
    any exception here and log it; the row will be cleaned up later by
    a manual sweep or the orphan cron.
    """
    try:
        await _mark_failed(sid)
    except Exception:
        log.exception("mark_failed_swallowed")


async def _publish_safe(
    publisher: StatusPublisher,
    sid: uuid.UUID,
    payload: dict[str, Any],
    log: structlog.stdlib.BoundLogger,
) -> None:
    """Best-effort publish.

    The DB is the source of truth — SSE is a UX convenience. A Redis
    blip while publishing must NOT roll back a successful commit, so
    we never re-raise here.
    """
    try:
        await publisher.publish(sid, payload)
    except Exception:
        log.warning("status_publish_swallowed", payload_status=payload.get("status"))


async def _publish_progress(
    publisher: StatusPublisher,
    sid: uuid.UUID,
    stage: str,
    log: structlog.stdlib.BoundLogger,
) -> None:
    """Publish an intermediate ``status: processing`` frame.

    Carries the same best-effort semantics as :func:`_publish_safe` —
    Redis blips never roll back DB work. The ``stage`` field lets the
    SSE consumer render a progress indicator without inventing its own
    timing heuristic.
    """
    await _publish_safe(
        publisher,
        sid,
        {
            "status": "processing",
            "storage_object_id": str(sid),
            "stage": stage,
        },
        log,
    )


@broker.task(
    task_name="image_process",
    queue_name="image.storage.process",
    retry_on_error=True,
    max_retries=2,
    timeout=300,
)
async def image_process_task(storage_object_id: str) -> None:
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

    await _publish_progress(publisher, sid, _PROGRESS_STAGE_STARTED, log)

    try:
        raw_data = await download_bytes(object_key)
        log.info("Downloaded raw", size=len(raw_data))
        await _publish_progress(publisher, sid, _PROGRESS_STAGE_DOWNLOADED, log)

        main_bytes, variants_meta, variants_data = await asyncio.to_thread(
            build_variants, raw_data, sid, settings.S3_PUBLIC_BASE_URL
        )
        await _publish_progress(publisher, sid, _PROGRESS_STAGE_VARIANTS_BUILT, log)

        main_key = f"public/{sid}.webp"
        await upload_bytes(main_key, main_bytes, "image/webp")
        for s3_key, data in variants_data.items():
            await upload_bytes(s3_key, data, "image/webp")
        await _publish_progress(publisher, sid, _PROGRESS_STAGE_UPLOADED, log)

        # Raw upload is now redundant — the WebP main + variants
        # carry the public surface. Best-effort cleanup: a failure
        # here is non-fatal because the orphan-cleanup cron will
        # sweep stale raw uploads on its 6-hourly run. Marking the
        # whole task FAILED for a transient S3 DELETE blip would
        # roll back a successful processing run.
        try:
            await delete_object(object_key)
        except Exception:
            log.warning(
                "raw_delete_swallowed_will_be_cleaned_by_orphan_cron",
                key=object_key,
            )

        public_url = f"{settings.S3_PUBLIC_BASE_URL.rstrip('/')}/{main_key}"
        await _mark_completed(sid, public_url, variants_meta, len(main_bytes))

    except _TERMINAL_PROCESSING_ERRORS as exc:
        # File-shape errors — retrying with the same bytes will fail
        # the same way. Mark FAILED + publish + swallow so TaskIQ does
        # NOT retry. The user gets a single ``failed`` SSE frame.
        log.warning("processing_failed_terminal", error=type(exc).__name__)
        await _mark_failed_safe(sid, log)
        await _publish_safe(
            publisher,
            sid,
            {
                "status": "failed",
                "storage_object_id": str(sid),
                "error": "Invalid image data",
            },
            log,
        )
        return

    except Exception:
        # Transient — re-raise so TaskIQ retries (up to ``max_retries``).
        # We still flip the row + publish a failure frame so the SSE
        # client doesn't sit on a stale PROCESSING; if a retry succeeds,
        # ``_mark_completed`` will flip the row back to COMPLETED and
        # the next publish will overwrite the SSE state with completed.
        log.exception("processing_failed_will_retry")
        await _mark_failed_safe(sid, log)
        await _publish_safe(
            publisher,
            sid,
            {
                "status": "failed",
                "storage_object_id": str(sid),
                "error": "Processing failed",
            },
            log,
        )
        raise

    # Success publish is isolated from the outer try so a Redis blip
    # while announcing completion does NOT undo a committed DB row
    # and uploaded WebPs (which the FAILED branch above would do).
    await _publish_safe(
        publisher,
        sid,
        {
            "status": "completed",
            "storage_object_id": str(sid),
            "url": public_url,
            "variants": variants_meta,
        },
        log,
    )
    log.info("Processing completed", url=public_url)


@broker.task(
    task_name="image_cleanup_orphans",
    queue_name="image.storage.cleanup_orphans",
    timeout=600,
    schedule=[{"cron": "0 */6 * * *"}],
)
async def image_cleanup_orphans_task() -> None:
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

    deleted = 0
    skipped = 0
    for orphan in orphans:
        try:
            await delete_object(orphan.object_key)
        except Exception:
            # S3 delete failed — leave the row in PENDING_UPLOAD so
            # the next cron run retries. Flipping to DELETED here
            # would leak the S3 object: the row says "deleted" so no
            # future sweep would look at it, but the bytes are still
            # in the bucket.
            log.warning(
                "orphan_s3_delete_failed_will_retry",
                key=orphan.object_key,
                id=str(orphan.id),
            )
            skipped += 1
            continue
        async with session_factory() as session, session.begin():
            await session.execute(
                text("UPDATE storage_objects SET status = :status WHERE id = :id"),
                {"id": orphan.id, "status": _STATUS_DELETED},
            )
        deleted += 1

    log.info("orphan_cleanup_done", deleted=deleted, skipped=skipped)
