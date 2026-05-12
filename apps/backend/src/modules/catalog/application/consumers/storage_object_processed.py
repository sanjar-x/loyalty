"""TaskIQ consumer that mirrors a re-processed storage object into ``media_assets`` (IMG-004).

Catalog denormalises ``url`` and ``image_variants`` from the image
module so storefront pages don't need a cross-module JOIN. The
denorm worked at create time but went stale on
``POST /admin/media/{id}/reupload`` — the storage_object_id stayed,
but its public URL changed when the worker re-encoded the new
upload, and admin product cards kept serving the old WebP.

This consumer subscribes to ``StorageObjectProcessedEvent`` (emitted
in ``image/infrastructure/tasks.py:process_image_task`` after the
worker finishes) and refreshes every ``MediaAsset`` row that
references the affected ``storage_object_id``.
"""

from __future__ import annotations

import uuid

import structlog
from dishka.integrations.taskiq import FromDishka, inject

from src.bootstrap.broker import broker
from src.modules.catalog.domain.interfaces import IMediaAssetRepository
from src.shared.interfaces.uow import IUnitOfWork

logger = structlog.get_logger(__name__)


@broker.task(
    queue="catalog_media_sync",
    exchange="taskiq_rpc_exchange",
    routing_key="catalog.media.sync_url",
    max_retries=3,
    retry_on_error=True,
    timeout=15,
)
@inject
async def sync_media_assets_on_processed(
    storage_object_id: str,
    url: str,
    image_variants: list[dict],
    media_repo: FromDishka[IMediaAssetRepository],
    uow: FromDishka[IUnitOfWork],
) -> dict:
    """Refresh ``url`` / ``image_variants`` on every ``MediaAsset``
    row that points at the just-processed storage object.

    Returns a small structured payload for observability:
    ``{"storage_object_id": ..., "updated_count": N}``.
    """
    sid = uuid.UUID(storage_object_id)
    log = logger.bind(storage_object_id=storage_object_id)

    affected = await media_repo.list_by_storage_ids([sid])
    if not affected:
        log.info("storage_object_processed_no_media_attached")
        return {"storage_object_id": storage_object_id, "updated_count": 0}

    async with uow:
        for media in affected:
            media.url = url
            media.image_variants = list(image_variants)
            await media_repo.update(media)
        await uow.commit()

    log.info(
        "media_asset_url_synced_after_processing",
        url=url,
        updated_count=len(affected),
    )
    return {"storage_object_id": storage_object_id, "updated_count": len(affected)}
