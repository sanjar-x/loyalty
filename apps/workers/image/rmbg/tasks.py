"""Image-rmbg consumer task — Bria RMBG-2.0 background removal.

Phase 5b extracted this body out of ``apps/backend/`` (where it used
to live at ``src/modules/image/infrastructure/tasks/rmbg.py``) into
this worker's directory. Backend now dispatches by task name only via
``broker.kicker().with_task_name("remove_background").kiq(...)`` and
never imports this module — the ML stack (torch, transformers, timm,
kornia) does not leak into backend's runtime graph.

Conditional registration on ``BG_REMOVAL_ENABLED``: the function body
is always defined at module level so it stays importable on developer
machines that don't have torch installed, but the broker decorator
only runs when the flag is on. ``apps/workers/image/rmbg``'s
environment flips it; every other deployment leaves it false.

Domain interfaces, ORM models, and shared services (SSE manager,
byte-stream helper) still live in backend and are imported
transitively via the workspace dependency.
"""

from __future__ import annotations

import uuid

import structlog
from dishka.integrations.taskiq import FromDishka, inject
from redis.asyncio import Redis

# Worker-local publisher — direct XADD writer, no dependency on
# backend's ``IChannelStream`` Protocol or ``SSEManager`` wrapper.
from publisher import StatusPublisher
from src.bootstrap.broker import broker
from src.bootstrap.config import Settings, settings
from src.modules.image.domain.events import BackgroundRemovedEvent
from src.modules.image.domain.interfaces import (
    IBackgroundRemover,
    IBlobStorage,
    IStorageRepository,
)
from src.modules.image.domain.value_objects import DerivationKind, StorageStatus
from src.modules.image.infrastructure.services.streams import bytes_to_async_stream
from src.shared.interfaces.uow import IUnitOfWork

logger = structlog.get_logger(__name__)


async def remove_background_task(
    derived_storage_object_id: str,
    blob_storage: FromDishka[IBlobStorage],
    storage_repo: FromDishka[IStorageRepository],
    uow: FromDishka[IUnitOfWork],
    settings: FromDishka[Settings],
    redis: FromDishka[Redis],
    bg_remover: FromDishka[IBackgroundRemover],
) -> None:
    """Run the ML cutout for a pre-provisioned derivation row.

    The ``RequestBackgroundRemovalHandler`` already inserted the
    PROCESSING placeholder so the SSE channel is addressable from the
    moment the HTTP 202 response left the API. This task fills in the
    real ``object_key`` / ``url`` / ``image_variants`` and pushes the
    completion / failure event.

    Run on a dedicated queue (``image.ml``) so the regular image-storage
    workers stay free of the ~1.6 GB model footprint. The matching
    Railway service (``apps/workers/image/rmbg``) installs torch +
    transformers + timm + kornia; every other service does not.
    """
    sid = uuid.UUID(derived_storage_object_id)
    log = logger.bind(derived_storage_object_id=derived_storage_object_id)
    log.info("background_removal_started")
    publisher = StatusPublisher(redis)

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
        # Pull the *processed* parent bytes — that's the public WebP the
        # storefront already serves, so the cutout always runs against
        # the same pixels the customer will see.
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
        # delete the placeholder from S3 because no upload was ever made
        # for it (it's just a DB-side string).

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

        await publisher.publish(
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
        await publisher.publish(
            sid,
            {
                "status": "failed",
                "storage_object_id": str(sid),
                "error": "Background removal failed",
                "kind": DerivationKind.BG_REMOVED.value,
            },
        )
        raise


# IMG-007 — conditional registration. The function body is always
# defined above so it remains importable on workers that don't enable
# bg-removal, but it is only wired to the broker (and therefore only
# starts subscribing to ``image.ml``) when the flag is on.
if settings.BG_REMOVAL_ENABLED:
    remove_background_task = broker.task(
        task_name="remove_background",
        queue_name="image.ml",
        retry_on_error=True,
        max_retries=2,
        timeout=240,
    )(inject(remove_background_task))
