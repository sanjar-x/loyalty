"""Media HTTP endpoints for the Image Backend microservice.

  POST   /media/upload               → reserve slot, return presigned PUT URL
  POST   /media/{id}/reupload        → replace image, keep same ID & URLs
  POST   /media/{id}/confirm         → verify S3, start background processing
  GET    /media/{id}/status           → SSE stream for processing status
  GET    /media/{id}                  → get metadata
  DELETE /media/{id}                  → delete files + record
  POST   /media/external             → import from external URL

All endpoints require API-key auth (X-API-Key header or api_key query param).
SSE uses native FastAPI (fastapi.sse) — ping, Cache-Control, X-Accel-Buffering
are handled automatically.
"""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import AsyncIterable

import httpx
from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, HTTPException, status
from fastapi.sse import EventSourceResponse, ServerSentEvent

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
    ReuploadRequest,
    ReuploadResponse,
    StatusEventData,
    UploadRequest,
    UploadResponse,
)
from src.modules.storage.presentation.sse import SSEManager
from src.modules.storage.presentation.tasks import process_image_task
from src.shared.interfaces.blob_storage import IBlobStorage
from src.shared.interfaces.config import IStorageConfig
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork

media_router = APIRouter(route_class=DishkaRoute)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
MAX_EXTERNAL_FILE_SIZE = 10 * 1024 * 1024  # 10 MB per spec


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
    repo: FromDishka[IStorageRepository],
    blob_storage: FromDishka[IBlobStorage],
    config: FromDishka[IStorageConfig],
    uow: FromDishka[IUnitOfWork],
) -> UploadResponse:
    filename = body.filename or f"upload.{body.content_type.split('/')[-1]}"

    # Create StorageFile record first to get the ID
    storage_file = StorageFile.create(
        bucket_name=config.S3_BUCKET_NAME,
        object_key="",  # placeholder, set below
        content_type=body.content_type,
        filename=filename,
    )

    # S3 key per spec: raw/{storage_object_id}/{filename}
    object_key = f"raw/{storage_file.id}/{filename}"
    storage_file.object_key = object_key

    # Generate presigned PUT URL
    presigned_url = await blob_storage.generate_presigned_put_url(
        object_name=object_key,
        content_type=body.content_type,
        expiration=300,
    )

    # Persist the record
    await repo.add(storage_file)
    await uow.commit()

    return UploadResponse(
        storage_object_id=storage_file.id,
        presigned_url=presigned_url,
        expires_in=300,
    )


# ---------------------------------------------------------------------------
# 2. POST /{storage_object_id}/reupload — Replace image, keep same ID & URLs
# ---------------------------------------------------------------------------
@media_router.post(
    "/{storage_object_id}/reupload",
    response_model=ReuploadResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a new presigned URL to replace the image (same ID & URLs)",
)
async def reupload(
    storage_object_id: uuid.UUID,
    body: ReuploadRequest,
    repo: FromDishka[IStorageRepository],
    blob_storage: FromDishka[IBlobStorage],
    uow: FromDishka[IUnitOfWork],
) -> ReuploadResponse:
    storage_file = await repo.get_by_id(storage_object_id)
    if not storage_file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Storage object not found.",
        )

    if storage_file.status == StorageStatus.PROCESSING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot reupload while image is being processed.",
        )

    filename = body.filename or f"upload.{body.content_type.split('/')[-1]}"

    # New raw key under the same ID — worker will overwrite public/{id}*.webp
    object_key = f"raw/{storage_object_id}/{filename}"

    presigned_url = await blob_storage.generate_presigned_put_url(
        object_name=object_key,
        content_type=body.content_type,
        expiration=300,
    )

    # Reset to PENDING_UPLOAD so confirm → processing → completed cycle restarts
    storage_file.object_key = object_key
    storage_file.content_type = body.content_type
    storage_file.filename = filename
    storage_file.status = StorageStatus.PENDING_UPLOAD
    await repo.update(storage_file)
    await uow.commit()

    return ReuploadResponse(
        storage_object_id=storage_object_id,
        presigned_url=presigned_url,
        expires_in=300,
    )


# ---------------------------------------------------------------------------
# 3. POST /{storage_object_id}/confirm — Verify S3, dispatch processing
# ---------------------------------------------------------------------------
@media_router.post(
    "/{storage_object_id}/confirm",
    response_model=ConfirmResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Confirm upload and start processing",
)
async def confirm_upload(
    storage_object_id: uuid.UUID,
    repo: FromDishka[IStorageRepository],
    blob_storage: FromDishka[IBlobStorage],
    uow: FromDishka[IUnitOfWork],
) -> ConfirmResponse:
    storage_file = await repo.get_by_id(storage_object_id)
    if not storage_file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Storage object not found.",
        )

    # Verify the file actually exists in S3 (HEAD check)
    exists = await blob_storage.object_exists(storage_file.object_key)
    if not exists:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="File not found in S3. Upload may not have completed.",
        )

    # Transition: PENDING_UPLOAD → PROCESSING
    storage_file.status = StorageStatus.PROCESSING
    await repo.update(storage_file)
    await uow.commit()

    # Dispatch background processing task
    await process_image_task.kiq(str(storage_object_id))

    return ConfirmResponse(storage_object_id=storage_object_id)


# ---------------------------------------------------------------------------
# 3. GET /{storage_object_id}/status — SSE stream for processing status
#
# Uses native FastAPI SSE (fastapi.sse). Built-in features:
#   • Keep-alive ping comment every 15s (automatic)
#   • Cache-Control: no-cache header (automatic)
#   • X-Accel-Buffering: no header (automatic)
# ---------------------------------------------------------------------------
@media_router.get(
    "/{storage_object_id}/status",
    response_class=EventSourceResponse,
    summary="Stream processing status via SSE",
)
async def stream_status(
    storage_object_id: uuid.UUID,
    repo: FromDishka[IStorageRepository],
    sse_manager: FromDishka[SSEManager],
) -> AsyncIterable[ServerSentEvent]:
    storage_file = await repo.get_by_id(storage_object_id)
    if not storage_file:
        yield ServerSentEvent(
            data={"error": "Storage object not found"},
            event="error",
        )
        return

    # Send current state on connect
    current = StatusEventData(
        status=storage_file.status.value,
        storage_object_id=storage_object_id,
        url=storage_file.url,
        variants=[MediaVariant(**v) for v in (storage_file.image_variants or [])],
    )
    yield ServerSentEvent(data=current.model_dump(by_alias=True), event="status")

    # If already terminal (completed/failed), close immediately
    if storage_file.status.is_terminal:
        return

    # Subscribe to Redis pub/sub for live updates
    async for event in sse_manager.subscribe(storage_object_id):
        if event is None:
            continue
        yield ServerSentEvent(data=event, event="status")
        if event.get("status") in ("completed", "failed"):
            return


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
        return DeleteResponse(deleted=True)  # idempotent

    # Build list of S3 keys to delete:
    # 1. raw file (if still exists)
    # 2. main processed file: public/{id}.webp
    # 3. variant files: public/{id}_{suffix}.webp
    keys_to_delete: list[str] = [storage_file.object_key]

    main_key = f"public/{storage_object_id}.webp"
    keys_to_delete.append(main_key)

    for suffix in ("thumb", "md", "lg"):
        keys_to_delete.append(f"public/{storage_object_id}_{suffix}.webp")

    # Best-effort S3 cleanup
    try:
        await blob_storage.delete_objects(keys_to_delete)
    except Exception:
        log.warning("Failed to batch-delete S3 objects", keys=keys_to_delete)

    # Soft-delete in DB
    await repo.mark_as_deleted(storage_file.bucket_name, storage_file.object_key)
    await uow.commit()

    log.info("Media deleted", keys=keys_to_delete)
    return DeleteResponse(deleted=True)


# ---------------------------------------------------------------------------
# 6. POST /external — Import from external URL (synchronous)
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

    # 1. Download (max 10 MB, 30s timeout per spec)
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(body.url, follow_redirects=True)
        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Failed to download image: HTTP {response.status_code}",
            )
        raw_data = response.content

    if len(raw_data) > MAX_EXTERNAL_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"File too large: {len(raw_data)} bytes (max {MAX_EXTERNAL_FILE_SIZE}).",
        )

    sid = uuid.uuid7() if hasattr(uuid, "uuid7") else uuid.uuid4()

    # 2. Process in thread (CPU-bound Pillow work)
    main_bytes, variants_meta, variants_data = await asyncio.to_thread(
        build_variants,
        raw_data,
        sid,
        config.S3_PUBLIC_BASE_URL,
    )

    # 3. Upload main + variants to S3
    main_key = f"public/{sid}.webp"
    await blob_storage.upload_stream(main_key, _bytes_stream(main_bytes), "image/webp")
    for s3_key, data in variants_data.items():
        await blob_storage.upload_stream(s3_key, _bytes_stream(data), "image/webp")

    # 4. Create DB record (already COMPLETED — no background processing needed)
    public_url = f"{config.S3_PUBLIC_BASE_URL.rstrip('/')}/{main_key}"

    storage_file = StorageFile(
        id=sid,
        bucket_name=config.S3_BUCKET_NAME,
        object_key=main_key,
        content_type="image/webp",
        size_bytes=len(main_bytes),
        owner_module="external",
        status=StorageStatus.COMPLETED,
        url=public_url,
        image_variants=variants_meta,
        filename=body.url.split("/")[-1].split("?")[0],
    )
    await repo.add(storage_file)
    await uow.commit()

    log.info("External import completed", storage_object_id=str(sid))

    return ExternalImportResponse(
        storage_object_id=sid,
        url=public_url,
        variants=[MediaVariant(**v) for v in variants_meta],
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
async def _bytes_stream(data: bytes):
    """Wrap bytes as an async iterator for upload_stream."""
    yield data
