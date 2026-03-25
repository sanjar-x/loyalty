"""Media HTTP endpoints for the Image Backend microservice.

Implements the full media lifecycle:
  1. POST /media/upload               — reserve slot, return presigned PUT URL
  2. POST /media/{id}/confirm          — verify S3, start background processing
  3. GET  /media/{id}/status            — SSE stream for processing status
  4. GET  /media/{id}                   — get metadata
  5. DELETE /media/{id}                 — delete files + record
  6. POST /media/external              — import from external URL
"""

import asyncio
import json
import uuid

import httpx
from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, HTTPException, status
from sse_starlette.sse import EventSourceResponse

from src.modules.storage.application.commands.process_image import build_variants
from src.modules.storage.domain.entities import StorageFile
from src.modules.storage.domain.interfaces import IStorageRepository
from src.modules.storage.domain.value_objects import StorageStatus
from src.modules.storage.presentation.schemas import (
    ConfirmResponse,
    DeleteResponse,
    ExternalImportRequest,
    ExternalImportResponse,
    MediaVariant,
    MetadataResponse,
    StatusEventData,
    UploadRequest,
    UploadResponse,
)
from src.modules.storage.presentation.sse import SSEManager
from src.modules.storage.presentation.tasks import process_image_task
from src.shared.interfaces.blob_storage import IBlobStorage
from src.shared.interfaces.config import IStorageConfig
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.storage import IStorageFacade
from src.shared.interfaces.uow import IUnitOfWork

media_router = APIRouter(route_class=DishkaRoute)


# ---------------------------------------------------------------------------
# 1. POST /upload — Reserve upload slot, return presigned PUT URL
# ---------------------------------------------------------------------------
@media_router.post(
    "/upload",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Reserve an upload slot and get a presigned PUT URL",
)
async def request_upload(
    body: UploadRequest,
    facade: FromDishka[IStorageFacade],
) -> UploadResponse:
    filename = body.filename or f"upload.{body.content_type.split('/')[-1]}"

    result = await facade.reserve_upload_slot(
        module="media",
        entity_id=str(uuid.uuid4()),
        filename=filename,
        content_type=body.content_type,
    )

    assert result.file_id is not None
    presigned_url = (
        result.url_data if isinstance(result.url_data, str) else result.url_data["url"]
    )
    return UploadResponse(
        storage_object_id=result.file_id,
        presigned_url=presigned_url,
    )


# ---------------------------------------------------------------------------
# 2. POST /{storage_object_id}/confirm — Verify S3, dispatch processing
# ---------------------------------------------------------------------------
@media_router.post(
    "/{storage_object_id}/confirm",
    response_model=ConfirmResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Confirm upload and start processing",
)
async def confirm_upload(
    storage_object_id: uuid.UUID,
    facade: FromDishka[IStorageFacade],
    repo: FromDishka[IStorageRepository],
    uow: FromDishka[IUnitOfWork],
) -> ConfirmResponse:
    # Verify the file exists in S3
    await facade.verify_upload(storage_object_id)

    # Transition to PROCESSING status
    async with uow:
        storage_file = await repo.get_by_id(storage_object_id)
        if not storage_file:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Storage object not found.",
            )
        storage_file.status = StorageStatus.PROCESSING
        await repo.update(storage_file)
        await uow.commit()

    # Dispatch background processing task
    await process_image_task.kiq(str(storage_object_id))

    return ConfirmResponse(storage_object_id=storage_object_id)


# ---------------------------------------------------------------------------
# 3. GET /{storage_object_id}/status — SSE stream for processing status
# ---------------------------------------------------------------------------
@media_router.get(
    "/{storage_object_id}/status",
    summary="Stream processing status via SSE",
)
async def stream_status(
    storage_object_id: uuid.UUID,
    repo: FromDishka[IStorageRepository],
    sse_manager: FromDishka[SSEManager],
) -> EventSourceResponse:
    async def _event_generator():
        # Send current state on connect
        storage_file = await repo.get_by_id(storage_object_id)
        if not storage_file:
            yield {
                "event": "error",
                "data": json.dumps({"error": "Storage object not found"}),
            }
            return

        current = StatusEventData(
            status=storage_file.status.value,
            storage_object_id=storage_object_id,
            url=storage_file.url,
            variants=[MediaVariant(**v) for v in (storage_file.image_variants or [])],
        )
        yield {"event": "status", "data": current.model_dump_json(by_alias=True)}

        # If already terminal, close immediately
        if storage_file.status.is_terminal:
            return

        # Subscribe to Redis pub/sub for live updates
        async for event in sse_manager.subscribe(storage_object_id):
            if event is None:
                # Heartbeat — keep connection alive
                yield {"event": "ping", "data": ""}
            else:
                yield {"event": "status", "data": json.dumps(event)}
                if event.get("status") in ("completed", "failed"):
                    return

    return EventSourceResponse(_event_generator())


# ---------------------------------------------------------------------------
# 4. GET /{storage_object_id} — Get metadata
# ---------------------------------------------------------------------------
@media_router.get(
    "/{storage_object_id}",
    response_model=MetadataResponse,
    summary="Get media metadata and variants",
)
async def get_metadata(
    storage_object_id: uuid.UUID,
    repo: FromDishka[IStorageRepository],
) -> MetadataResponse:
    storage_file = await repo.get_by_id(storage_object_id)
    if not storage_file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Storage object not found.",
        )

    return MetadataResponse(
        storage_object_id=storage_file.id,
        status=storage_file.status.value,
        url=storage_file.url,
        content_type=storage_file.content_type,
        size_bytes=storage_file.size_bytes,
        variants=[MediaVariant(**v) for v in (storage_file.image_variants or [])],
        created_at=storage_file.created_at,
    )


# ---------------------------------------------------------------------------
# 5. DELETE /{storage_object_id} — Delete files + record (idempotent)
# ---------------------------------------------------------------------------
@media_router.delete(
    "/{storage_object_id}",
    response_model=DeleteResponse,
    summary="Delete media object and all variants",
)
async def delete_media(
    storage_object_id: uuid.UUID,
    repo: FromDishka[IStorageRepository],
    blob_storage: FromDishka[IBlobStorage],
    uow: FromDishka[IUnitOfWork],
    logger: FromDishka[ILogger],
) -> DeleteResponse:
    log = logger.bind(storage_object_id=str(storage_object_id))

    storage_file = await repo.get_by_id(storage_object_id)
    if not storage_file:
        # Idempotent: return success even if not found
        return DeleteResponse(deleted=True)

    # Collect all S3 keys to delete (raw + variants)
    keys_to_delete: list[str] = [storage_file.object_key]
    if storage_file.image_variants:
        for variant in storage_file.image_variants:
            url: str = variant.get("url", "")
            # Extract key from full URL if needed
            if "/" in url:
                # Variant URLs look like {base_url}/public/{id}_{suffix}.webp
                key_part = url.split("/public/", 1)
                if len(key_part) == 2:
                    keys_to_delete.append(f"public/{key_part[1]}")

    # Also delete the main processed file if it exists
    main_key = f"public/{storage_object_id}.webp"
    if main_key not in keys_to_delete:
        keys_to_delete.append(main_key)

    # Delete from S3 (best-effort)
    for key in keys_to_delete:
        try:
            await blob_storage.delete_object(key)
        except Exception:
            log.warning("Failed to delete S3 object", key=key)

    # Soft-delete in DB
    async with uow:
        await repo.mark_as_deleted(storage_file.bucket_name, storage_file.object_key)
        await uow.commit()

    log.info("Media deleted", keys=keys_to_delete)
    return DeleteResponse(deleted=True)


# ---------------------------------------------------------------------------
# 6. POST /external — Import from external URL
# ---------------------------------------------------------------------------
@media_router.post(
    "/external",
    response_model=ExternalImportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Import media from an external URL",
)
async def import_external(
    body: ExternalImportRequest,
    blob_storage: FromDishka[IBlobStorage],
    repo: FromDishka[IStorageRepository],
    uow: FromDishka[IUnitOfWork],
    config: FromDishka[IStorageConfig],
    logger: FromDishka[ILogger],
) -> ExternalImportResponse:
    log = logger.bind(external_url=body.url)
    log.info("External import started")

    # 1. Download the image from the external URL
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(body.url)
        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Failed to download image: HTTP {response.status_code}",
            )
        raw_data = response.content

    storage_object_id = uuid.uuid7() if hasattr(uuid, "uuid7") else uuid.uuid4()

    # 2. Process in thread (CPU-bound)
    main_bytes, variants_meta, variants_data = await asyncio.to_thread(
        build_variants, raw_data, storage_object_id, config.S3_PUBLIC_BASE_URL
    )

    # 3. Upload main file to S3
    main_key = f"public/{storage_object_id}.webp"
    await blob_storage.upload_stream(
        main_key, _bytes_to_stream(main_bytes), "image/webp"
    )

    # 4. Upload variants to S3
    for s3_key, data in variants_data.items():
        await blob_storage.upload_stream(s3_key, _bytes_to_stream(data), "image/webp")

    # 5. Create DB record
    public_url = f"{config.S3_PUBLIC_BASE_URL.rstrip('/')}/{main_key}"

    storage_file = StorageFile(
        id=storage_object_id,
        bucket_name=config.S3_BUCKET_NAME,
        object_key=main_key,
        content_type="image/webp",
        size_bytes=len(main_bytes),
        owner_module="external",
        status=StorageStatus.COMPLETED,
        url=public_url,
        image_variants=variants_meta,
    )

    async with uow:
        await repo.add(storage_file)
        await uow.commit()

    log.info("External import completed", storage_object_id=str(storage_object_id))

    return ExternalImportResponse(
        storage_object_id=storage_object_id,
        url=public_url,
        variants=[MediaVariant(**v) for v in variants_meta],
    )


async def _bytes_to_stream(data: bytes):
    """Wrap bytes as an async iterator for upload_stream."""
    yield data
