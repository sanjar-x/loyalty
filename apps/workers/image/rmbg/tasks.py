"""Image-rmbg worker tasks — Bria RMBG-2.0, no backend imports.

* ``image_remove_background_task`` — downloads the processed parent
  WebP from S3, runs Bria RMBG-2.0 inference, uploads the cutout,
  updates the derived row, writes the BackgroundRemovedEvent to the
  outbox and pushes a status frame to Redis Streams.

Coordination with backend happens through three external surfaces:

* PostgreSQL — the ``storage_objects`` + ``outbox_messages`` tables
  (schema owned by backend's alembic migrations).
* Redis Streams — channel ``media:status:{uuid}``.
* RabbitMQ task name ``image_remove_background`` published with
  routing key ``image.rmbg.remove`` (bound to ``image_rmbg_jobs``).

No Python import crosses the boundary.
"""

from __future__ import annotations

import json
import uuid
from typing import Any

import structlog
from PIL import Image, UnidentifiedImageError
from sqlalchemy import text

from bria_rmbg import BriaRMBGPermanentInitError, bria_rmbg
from broker import broker
from config import settings
from db import session_factory
from publisher import StatusPublisher
from redis_client import redis_client
from s3 import download_bytes, upload_bytes

# Errors we know we cannot recover from by retrying. Two flavours:
#
# * Payload-driven (``UnidentifiedImageError``, ``DecompressionBombError``):
#   the parent WebP itself is bad — retrying with the same bytes will
#   fail the same way.
# * Worker-config-driven (``BriaRMBGPermanentInitError``): bad HF token,
#   gated repo, or missing model. Every task on this worker will fail
#   identically until the operator fixes config and restarts; fail
#   fast and surface FAILED frames quickly so the operator notices.
#
# Anything else (CUDA OOM, S3 timeout, asyncpg disconnect, Redis blip,
# transient HF download error) is treated as recoverable and re-raised
# so TaskIQ retries.
_TERMINAL_PROCESSING_ERRORS: tuple[type[BaseException], ...] = (
    UnidentifiedImageError,
    Image.DecompressionBombError,
    BriaRMBGPermanentInitError,
)

logger = structlog.get_logger(__name__)

_STATUS_COMPLETED = "COMPLETED"
_STATUS_FAILED = "FAILED"

# Outbox event metadata — must match :class:`ImageEvent` in
# ``apps/backend/src/modules/image/domain/events.py``. The
# ``aggregate_type`` is the bounded-context label, NOT the SQL table
# name; ``BackgroundRemovedEvent`` belongs to the ``image`` context.
_AGGREGATE_TYPE = "image"
_EVENT_TYPE_BG_REMOVED = "BackgroundRemovedEvent"
_DERIVATION_KIND_BG_REMOVED = "bg_removed"

# Progress stages emitted between ``status: processing`` start and the
# terminal ``status: completed`` / ``status: failed`` frames. Stage
# names are part of the wire contract with the SSE subscriber — adding
# or renaming one is a breaking change. ``started``, ``downloaded``,
# ``uploaded`` are aligned with the storage worker's sibling vocabulary;
# ``inference_done`` is rmbg-specific (CPU/GPU heavy step).
_PROGRESS_STAGE_STARTED = "started"
_PROGRESS_STAGE_DOWNLOADED = "downloaded"
_PROGRESS_STAGE_INFERENCE_DONE = "inference_done"
_PROGRESS_STAGE_UPLOADED = "uploaded"


async def _fetch_derivation(
    sid: uuid.UUID,
) -> tuple[uuid.UUID, str] | None:
    """Return ``(parent_storage_object_id, parent_processed_key)``."""
    async with session_factory() as session:
        result = await session.execute(
            text("SELECT parent_storage_object_id FROM storage_objects WHERE id = :id"),
            {"id": sid},
        )
        row = result.first()
        if row is None or row.parent_storage_object_id is None:
            return None
        parent_id = row.parent_storage_object_id

    # Parent's processed WebP lives at the deterministic key
    # ``public/{parent_id}.webp`` — established by the storage worker
    # when it finished ``image_process_task``.
    return parent_id, f"public/{parent_id}.webp"


async def _mark_completed(
    sid: uuid.UUID,
    parent_id: uuid.UUID,
    cutout_key: str,
    public_url: str,
    cutout_size: int,
) -> None:
    """Update the derived row to COMPLETED and append the bg-removed
    event to the outbox in the same transaction.
    """
    payload = {
        "storage_object_id": str(sid),
        "parent_storage_object_id": str(parent_id),
        "url": public_url,
        "derivation_kind": _DERIVATION_KIND_BG_REMOVED,
        "image_variants": [],
    }
    async with session_factory() as session, session.begin():
        await session.execute(
            text(
                "UPDATE storage_objects "
                "SET status = :status, object_key = :object_key, "
                "    url = :url, size_bytes = :size, "
                "    content_type = :content_type, "
                "    image_variants = '[]'::jsonb "
                "WHERE id = :id"
            ),
            {
                "id": sid,
                "status": _STATUS_COMPLETED,
                "object_key": cutout_key,
                "url": public_url,
                "size": cutout_size,
                "content_type": bria_rmbg.output_content_type,
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
                "event_type": _EVENT_TYPE_BG_REMOVED,
                "payload": json.dumps(payload),
            },
        )


async def _mark_failed(sid: uuid.UUID) -> None:
    async with session_factory() as session, session.begin():
        await session.execute(
            text("UPDATE storage_objects SET status = :status WHERE id = :id"),
            {"id": sid, "status": _STATUS_FAILED},
        )


async def _mark_failed_safe(sid: uuid.UUID, log: structlog.stdlib.BoundLogger) -> None:
    """Best-effort wrapper around :func:`_mark_failed`. See the storage
    worker's twin for the rationale — we never let a secondary error
    on the failure path swallow the failure SSE frame.
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
    """Best-effort publish — Redis is a UX convenience, not the source
    of truth. A blip here must not roll back the DB commit.
    """
    try:
        await publisher.publish(sid, payload)
    except Exception:
        log.warning(
            "status_publish_swallowed",
            payload_status=payload.get("status"),
        )


async def _publish_progress(
    publisher: StatusPublisher,
    sid: uuid.UUID,
    stage: str,
    log: structlog.stdlib.BoundLogger,
) -> None:
    """Publish an intermediate ``status: processing`` frame.

    Carries the same best-effort semantics as :func:`_publish_safe` —
    Redis blips never roll back DB work. ``kind`` is included so the
    SSE consumer can distinguish bg-removed progress frames from
    parent-upload progress on the same channel-naming pattern.
    """
    await _publish_safe(
        publisher,
        sid,
        {
            "status": "processing",
            "storage_object_id": str(sid),
            "stage": stage,
            "kind": _DERIVATION_KIND_BG_REMOVED,
        },
        log,
    )


@broker.task(
    task_name="image_remove_background",
    queue_name="image.rmbg.remove",
    retry_on_error=True,
    max_retries=2,
    timeout=240,
)
async def image_remove_background_task(derived_storage_object_id: str) -> None:
    """Run Bria RMBG-2.0 inference for a pre-provisioned derivation row."""
    sid = uuid.UUID(derived_storage_object_id)
    log = logger.bind(derived_storage_object_id=derived_storage_object_id)
    log.info("background_removal_started")
    publisher = StatusPublisher(redis_client)

    fetched = await _fetch_derivation(sid)
    if fetched is None:
        log.error("derived_storage_object_missing_or_not_a_derivation")
        return
    parent_id, processed_key = fetched

    await _publish_progress(publisher, sid, _PROGRESS_STAGE_STARTED, log)

    try:
        parent_bytes = await download_bytes(processed_key)
        log.info("parent_bytes_fetched", size=len(parent_bytes))
        await _publish_progress(publisher, sid, _PROGRESS_STAGE_DOWNLOADED, log)

        cutout_bytes = await bria_rmbg.remove(parent_bytes)
        log.info("inference_done", cutout_size=len(cutout_bytes))
        await _publish_progress(
            publisher, sid, _PROGRESS_STAGE_INFERENCE_DONE, log
        )

        cutout_key = f"public/{sid}_bg_removed.webp"
        await upload_bytes(cutout_key, cutout_bytes, bria_rmbg.output_content_type)
        await _publish_progress(publisher, sid, _PROGRESS_STAGE_UPLOADED, log)

        public_url = f"{settings.S3_PUBLIC_BASE_URL.rstrip('/')}/{cutout_key}"
        await _mark_completed(sid, parent_id, cutout_key, public_url, len(cutout_bytes))

    except _TERMINAL_PROCESSING_ERRORS as exc:
        # The parent WebP is corrupt — retrying with the same bytes
        # will fail the same way. Mark FAILED + publish + return so
        # TaskIQ does NOT retry.
        log.warning(
            "background_removal_failed_terminal",
            error=type(exc).__name__,
        )
        await _mark_failed_safe(sid, log)
        await _publish_safe(
            publisher,
            sid,
            {
                "status": "failed",
                "storage_object_id": str(sid),
                "error": "Invalid parent image",
                "kind": _DERIVATION_KIND_BG_REMOVED,
            },
            log,
        )
        return

    except Exception:
        # Transient — re-raise so TaskIQ retries (up to ``max_retries``).
        # The mark-failed + publish below land before the retry so the
        # SSE client sees a failure frame promptly; if a retry succeeds,
        # ``_mark_completed`` flips the row back and the success frame
        # overwrites the SSE state.
        log.exception("background_removal_failed_will_retry")
        await _mark_failed_safe(sid, log)
        await _publish_safe(
            publisher,
            sid,
            {
                "status": "failed",
                "storage_object_id": str(sid),
                "error": "Background removal failed",
                "kind": _DERIVATION_KIND_BG_REMOVED,
            },
            log,
        )
        raise

    # Success publish is isolated from the outer try so a Redis blip
    # while announcing completion does NOT undo a committed DB row
    # and uploaded cutout (which the FAILED branch above would do).
    await _publish_safe(
        publisher,
        sid,
        {
            "status": "completed",
            "storage_object_id": str(sid),
            "url": public_url,
            "variants": [],
            "kind": _DERIVATION_KIND_BG_REMOVED,
        },
        log,
    )
    log.info("background_removal_completed", url=public_url)
