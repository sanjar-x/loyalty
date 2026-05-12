"""TaskIQ consumer that drops the storage object after catalog detached
the corresponding media asset (IMG-005).

Replaces the prior best-effort post-commit ``media_cleanup.delete`` loop
in ``UpdateProductHandler``. With the loop, a process crash after the
DB commit but before the S3 delete left an orphan that
``cleanup_orphans_task`` did not pick up (it only sweeps
``PENDING_UPLOAD`` rows, not COMPLETED-but-orphaned).

Now the cleanup runs via TaskIQ after the relay picks up
``MediaAssetDetachedEvent`` from the outbox. At-least-once delivery
plus retry budget on the task means orphans are eventually cleaned
even if the worker crashes mid-delete.
"""

from __future__ import annotations

import uuid

import structlog
from dishka.integrations.taskiq import FromDishka, inject

from src.bootstrap.broker import broker
from src.modules.catalog.domain.interfaces import IMediaCleanupPort

logger = structlog.get_logger(__name__)


@broker.task(
    queue="catalog_media_cleanup",
    exchange="taskiq_rpc_exchange",
    routing_key="catalog.media.cleanup_storage",
    max_retries=3,
    retry_on_error=True,
    timeout=30,
)
@inject
async def cleanup_storage_after_detached(
    storage_object_id: str,
    cleanup: FromDishka[IMediaCleanupPort],
) -> dict:
    """Best-effort delete of the S3 keys + soft-delete the DB row.

    Idempotent: the underlying ``DeleteStorageObjectHandler`` reached
    via :class:`IMediaCleanupPort` short-circuits when the row is
    already gone, so an at-least-once retry from the outbox relay
    never produces a duplicate operation or surfaces an error.

    We go through ``IMediaCleanupPort`` (and not the image-module
    handler directly) because the cross-module boundary is enforced
    by ``tests/architecture/test_boundaries.py`` —
    ``catalog.application`` is forbidden to import
    ``image.application``.  The adapter that implements the port lives
    in ``catalog/infrastructure/adapters/media_cleanup_adapter.py``
    and is the whitelisted seam.
    """
    sid = uuid.UUID(storage_object_id)
    log = logger.bind(storage_object_id=storage_object_id)

    try:
        await cleanup.delete(sid)
    except Exception:
        # Surface the failure so TaskIQ retries (and eventually lands
        # the row in failed_tasks for ops to investigate). The
        # underlying handler already swallows S3 errors as warnings —
        # this catch fires for unexpected programmer bugs only.
        log.exception("media_cleanup_after_detached_failed")
        raise

    log.info("media_cleanup_after_detached_ok")
    return {"storage_object_id": storage_object_id, "ok": True}
