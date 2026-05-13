"""Image-rmbg worker tasks — Bria RMBG-2.0, no backend imports.

* ``remove_background_task`` — downloads the processed parent WebP from
  S3, runs Bria RMBG-2.0 inference, uploads the cutout, updates the
  derived row, writes the BackgroundRemovedEvent to the outbox and
  pushes a status frame to Redis Streams.

Coordination with backend happens through three external surfaces:

* PostgreSQL — the ``storage_objects`` + ``outbox_messages`` tables
  (schema owned by backend's alembic migrations).
* Redis Streams — channel ``media:status:{uuid}``.
* RabbitMQ task name ``remove_background`` (queue ``image.ml``).

No Python import crosses the boundary. Conditional registration on
the broker is intentional: the worker may be deployed with the model
weights pre-warmed, or without (in which case it skips registering
the task and never subscribes to ``image.ml``).
"""

from __future__ import annotations

import json
import uuid

import structlog
from sqlalchemy import text

from bria_rmbg import bria_rmbg
from broker import broker
from config import settings
from db import session_factory
from publisher import StatusPublisher
from redis_client import redis_client
from s3 import download_bytes, upload_bytes

logger = structlog.get_logger(__name__)

_STATUS_COMPLETED = "COMPLETED"
_STATUS_FAILED = "FAILED"

_AGGREGATE_TYPE = "StorageObject"
_EVENT_TYPE_BG_REMOVED = "BackgroundRemovedEvent"
_DERIVATION_KIND_BG_REMOVED = "bg_removed"


async def _fetch_derivation(
    sid: uuid.UUID,
) -> tuple[uuid.UUID, str] | None:
    """Return ``(parent_storage_object_id, parent_processed_key)``."""
    async with session_factory() as session:
        result = await session.execute(
            text(
                "SELECT parent_storage_object_id FROM storage_objects "
                "WHERE id = :id"
            ),
            {"id": sid},
        )
        row = result.first()
        if row is None or row.parent_storage_object_id is None:
            return None
        parent_id = row.parent_storage_object_id

    # Parent's processed WebP lives at the deterministic key
    # ``public/{parent_id}.webp`` — established by the storage worker
    # when it finished ``process_image_task``.
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
            text(
                "UPDATE storage_objects SET status = :status WHERE id = :id"
            ),
            {"id": sid, "status": _STATUS_FAILED},
        )


@broker.task(
    task_name="remove_background",
    queue_name="image.ml",
    retry_on_error=True,
    max_retries=2,
    timeout=240,
)
async def remove_background_task(derived_storage_object_id: str) -> None:
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

    try:
        parent_bytes = await download_bytes(processed_key)
        log.info("parent_bytes_fetched", size=len(parent_bytes))

        cutout_bytes = await bria_rmbg.remove(parent_bytes)
        log.info("inference_done", cutout_size=len(cutout_bytes))

        cutout_key = f"public/{sid}_bg_removed.webp"
        await upload_bytes(
            cutout_key, cutout_bytes, bria_rmbg.output_content_type
        )

        public_url = (
            f"{settings.S3_PUBLIC_BASE_URL.rstrip('/')}/{cutout_key}"
        )
        await _mark_completed(
            sid, parent_id, cutout_key, public_url, len(cutout_bytes)
        )

        await publisher.publish(
            sid,
            {
                "status": "completed",
                "storage_object_id": str(sid),
                "url": public_url,
                "variants": [],
                "kind": _DERIVATION_KIND_BG_REMOVED,
            },
        )
        log.info("background_removal_completed", url=public_url)

    except Exception:
        log.exception("background_removal_failed")
        await _mark_failed(sid)
        await publisher.publish(
            sid,
            {
                "status": "failed",
                "storage_object_id": str(sid),
                "error": "Background removal failed",
                "kind": _DERIVATION_KIND_BG_REMOVED,
            },
        )
        raise
