"""Image module admin router (staff-only).

  POST   /admin/media/upload                   reserve slot, return presigned PUT URL
  POST   /admin/media/{id}/reupload            replace image, keep same ID & URLs
  POST   /admin/media/{id}/confirm             verify S3, dispatch processing
  GET    /admin/media/{id}/status              SSE stream for processing status
  GET    /admin/media/{id}                      get metadata
  DELETE /admin/media/{id}                      delete files + record
  POST   /admin/media/external                 import from external URL

Auth: staff JWT + ``RequirePermission("media:manage")`` per route. Replaces
the X-API-Key model used by the legacy ``image_backend`` microservice
(CEO directive 2026-05-08, β: full JWT migration).
"""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import AsyncIterable

import httpx
import structlog
from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Depends, status
from fastapi.sse import EventSourceResponse, ServerSentEvent
from sqlalchemy.ext.asyncio import AsyncSession

from src.bootstrap.config import Settings
from src.modules.identity.presentation.dependencies import RequirePermission
from src.modules.image.application.commands.delete_storage_object import (
    DeleteStorageObjectHandler,
)
from src.modules.image.domain.entities import StorageFile
from src.modules.image.domain.exceptions import (
    StorageFileAlreadyProcessedError,
    StorageFileNotFoundError,
)
from src.modules.image.domain.interfaces import IBlobStorage, IStorageRepository
from src.modules.image.domain.value_objects import StorageStatus
from src.modules.image.infrastructure.services.image_processor import build_variants
from src.modules.image.infrastructure.services.sse_manager import SSEManager
from src.modules.image.infrastructure.services.streams import bytes_to_async_stream
from src.modules.image.infrastructure.tasks import process_image_task
from src.modules.image.presentation.schemas import (
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
from src.modules.image.presentation.validators import (
    validate_external_url,
    validate_image_content_type,
)
from src.shared.exceptions import (
    ConflictError,
    UnprocessableEntityError,
)
from src.shared.interfaces.uow import IUnitOfWork

logger = structlog.get_logger(__name__)

media_admin_router = APIRouter(
    prefix="/admin/media",
    tags=["Admin / Media"],
    route_class=DishkaRoute,
)

_MEDIA_PERMISSION = "media:manage"


# ---------------------------------------------------------------------------
# 1. POST /upload — Reserve upload slot, return presigned PUT URL
# ---------------------------------------------------------------------------
@media_admin_router.post(
    "/upload",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Reserve an upload slot and get a presigned PUT URL",
    dependencies=[Depends(RequirePermission(codename=_MEDIA_PERMISSION))],
)
async def request_upload(
    body: UploadRequest,
    repo: FromDishka[IStorageRepository],
    blob_storage: FromDishka[IBlobStorage],
    settings: FromDishka[Settings],
    uow: FromDishka[IUnitOfWork],
) -> UploadResponse:
    validate_image_content_type(body.content_type)

    filename = body.filename or f"upload.{body.content_type.split('/')[-1]}"

    storage_file = StorageFile.create(
        bucket_name=settings.S3_BUCKET_NAME,
        object_key="",
        content_type=body.content_type,
        filename=filename,
    )
    object_key = f"raw/{storage_file.id}/{filename}"
    storage_file.object_key = object_key

    presigned_url = await blob_storage.generate_presigned_put_url(
        object_name=object_key,
        content_type=body.content_type,
        expiration=settings.MEDIA_PRESIGNED_URL_TTL,
    )

    await repo.add(storage_file)
    await uow.commit()

    return UploadResponse(
        storage_object_id=storage_file.id,
        presigned_url=presigned_url,
        expires_in=settings.MEDIA_PRESIGNED_URL_TTL,
    )


# ---------------------------------------------------------------------------
# 2. POST /{storage_object_id}/reupload — Replace image, keep same ID & URLs
# ---------------------------------------------------------------------------
@media_admin_router.post(
    "/{storage_object_id}/reupload",
    response_model=ReuploadResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a new presigned URL to replace the image (same ID & URLs)",
    dependencies=[Depends(RequirePermission(codename=_MEDIA_PERMISSION))],
)
async def reupload(
    storage_object_id: uuid.UUID,
    body: ReuploadRequest,
    repo: FromDishka[IStorageRepository],
    blob_storage: FromDishka[IBlobStorage],
    settings: FromDishka[Settings],
    uow: FromDishka[IUnitOfWork],
) -> ReuploadResponse:
    storage_file = await repo.get_by_id(storage_object_id)
    if not storage_file:
        raise StorageFileNotFoundError(storage_object_id=str(storage_object_id))

    if storage_file.status == StorageStatus.PROCESSING:
        raise ConflictError(
            message="Cannot reupload while image is being processed.",
            error_code="STORAGE_FILE_PROCESSING_IN_PROGRESS",
            details={"storage_object_id": str(storage_object_id)},
        )

    validate_image_content_type(body.content_type)
    filename = body.filename or f"upload.{body.content_type.split('/')[-1]}"
    object_key = f"raw/{storage_object_id}/{filename}"

    presigned_url = await blob_storage.generate_presigned_put_url(
        object_name=object_key,
        content_type=body.content_type,
        expiration=settings.MEDIA_PRESIGNED_URL_TTL,
    )

    storage_file.object_key = object_key
    storage_file.content_type = body.content_type
    storage_file.filename = filename
    storage_file.status = StorageStatus.PENDING_UPLOAD
    await repo.update(storage_file)
    await uow.commit()

    return ReuploadResponse(
        storage_object_id=storage_object_id,
        presigned_url=presigned_url,
        expires_in=settings.MEDIA_PRESIGNED_URL_TTL,
    )


# ---------------------------------------------------------------------------
# 3. POST /{storage_object_id}/confirm — Verify S3, dispatch processing
# ---------------------------------------------------------------------------
@media_admin_router.post(
    "/{storage_object_id}/confirm",
    response_model=ConfirmResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Confirm upload and start processing",
    dependencies=[Depends(RequirePermission(codename=_MEDIA_PERMISSION))],
)
async def confirm_upload(
    storage_object_id: uuid.UUID,
    repo: FromDishka[IStorageRepository],
    blob_storage: FromDishka[IBlobStorage],
    uow: FromDishka[IUnitOfWork],
    settings: FromDishka[Settings],
) -> ConfirmResponse:
    storage_file = await repo.get_by_id(storage_object_id)
    if not storage_file:
        raise StorageFileNotFoundError(storage_object_id=str(storage_object_id))

    if storage_file.status != StorageStatus.PENDING_UPLOAD:
        raise StorageFileAlreadyProcessedError(storage_object_id=str(storage_object_id))

    metadata = await blob_storage.get_object_metadata(storage_file.object_key)
    if not metadata:
        raise UnprocessableEntityError(
            message="File not found in S3. Upload may not have completed.",
            error_code="STORAGE_OBJECT_NOT_UPLOADED",
            details={"storage_object_id": str(storage_object_id)},
        )

    file_size = metadata.get("content_length", 0)
    if file_size > settings.MEDIA_MAX_FILE_SIZE:
        raise UnprocessableEntityError(
            message=f"File too large: {file_size} bytes (max {settings.MEDIA_MAX_FILE_SIZE}).",
            error_code="STORAGE_OBJECT_TOO_LARGE",
            details={
                "storage_object_id": str(storage_object_id),
                "size": file_size,
                "max": settings.MEDIA_MAX_FILE_SIZE,
            },
        )

    storage_file.status = StorageStatus.PROCESSING
    await repo.update(storage_file)
    await uow.commit()

    await process_image_task.kiq(str(storage_object_id))  # ty:ignore[no-matching-overload]

    return ConfirmResponse(storage_object_id=storage_object_id)


# ---------------------------------------------------------------------------
# 4. GET /{storage_object_id}/status — SSE stream for processing status
# ---------------------------------------------------------------------------
@media_admin_router.get(
    "/{storage_object_id}/status",
    response_class=EventSourceResponse,
    summary="Stream processing status via SSE",
    dependencies=[Depends(RequirePermission(codename=_MEDIA_PERMISSION))],
)
async def stream_status(
    storage_object_id: uuid.UUID,
    repo: FromDishka[IStorageRepository],
    sse_manager: FromDishka[SSEManager],
    session: FromDishka[AsyncSession],
) -> AsyncIterable[ServerSentEvent]:
    storage_file = await repo.get_by_id(storage_object_id)
    # Release the DB connection: the SSE loop polls Redis for up to 120s
    # and would otherwise hold an idle-in-transaction session, which
    # Postgres' idle_in_transaction_session_timeout would kill mid-stream.
    await session.close()

    if not storage_file:
        yield ServerSentEvent(
            data={"error": "Storage object not found"},
            event="error",
        )
        return

    current = StatusEventData(
        status=storage_file.status.value,
        storage_object_id=storage_object_id,
        url=storage_file.url,
        variants=[MediaVariant(**v) for v in (storage_file.image_variants or [])],
    )
    yield ServerSentEvent(data=current.model_dump(by_alias=True), event="status")

    if storage_file.status.is_terminal:
        return

    async for event in sse_manager.subscribe(storage_object_id):
        if event is None:
            continue
        yield ServerSentEvent(data=event, event="status")
        if event.get("status") in ("completed", "failed"):
            return


# ---------------------------------------------------------------------------
# 5. GET /{storage_object_id} — Get metadata
# ---------------------------------------------------------------------------
@media_admin_router.get(
    "/{storage_object_id}",
    response_model=MetadataResponse,
    summary="Get media metadata and variants",
    dependencies=[Depends(RequirePermission(codename=_MEDIA_PERMISSION))],
)
async def get_metadata(
    storage_object_id: uuid.UUID,
    repo: FromDishka[IStorageRepository],
) -> MetadataResponse:
    storage_file = await repo.get_by_id(storage_object_id)
    if not storage_file:
        raise StorageFileNotFoundError(storage_object_id=str(storage_object_id))

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
# 6. DELETE /{storage_object_id} — Delete files + record (idempotent)
# ---------------------------------------------------------------------------
@media_admin_router.delete(
    "/{storage_object_id}",
    response_model=DeleteResponse,
    summary="Delete media object and all variants",
    dependencies=[Depends(RequirePermission(codename=_MEDIA_PERMISSION))],
)
async def delete_media(
    storage_object_id: uuid.UUID,
    handler: FromDishka[DeleteStorageObjectHandler],
) -> DeleteResponse:
    """Idempotent — handler is a no-op when the object doesn't exist."""
    await handler.handle(storage_object_id)
    return DeleteResponse(deleted=True)


# ---------------------------------------------------------------------------
# 7. POST /external — Import from external URL (synchronous)
# ---------------------------------------------------------------------------
@media_admin_router.post(
    "/external",
    response_model=ExternalImportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Import media from an external URL",
    dependencies=[Depends(RequirePermission(codename=_MEDIA_PERMISSION))],
)
async def import_external(
    body: ExternalImportRequest,
    blob_storage: FromDishka[IBlobStorage],
    repo: FromDishka[IStorageRepository],
    uow: FromDishka[IUnitOfWork],
    settings: FromDishka[Settings],
) -> ExternalImportResponse:
    log = logger.bind(external_url=body.url)
    log.info("External import started")

    validate_external_url(body.url)

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(body.url, follow_redirects=True)
        if response.status_code != 200:
            raise UnprocessableEntityError(
                message=f"Failed to download image: HTTP {response.status_code}",
                error_code="EXTERNAL_IMPORT_DOWNLOAD_FAILED",
                details={"url": body.url, "status": response.status_code},
            )
        raw_data = response.content

    if len(raw_data) > settings.MEDIA_MAX_FILE_SIZE:
        raise UnprocessableEntityError(
            message=f"File too large: {len(raw_data)} bytes (max {settings.MEDIA_MAX_FILE_SIZE}).",
            error_code="STORAGE_OBJECT_TOO_LARGE",
            details={"size": len(raw_data), "max": settings.MEDIA_MAX_FILE_SIZE},
        )

    sid = uuid.uuid7() if hasattr(uuid, "uuid7") else uuid.uuid4()

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

    public_url = f"{settings.S3_PUBLIC_BASE_URL.rstrip('/')}/{main_key}"

    storage_file = StorageFile(
        id=sid,
        bucket_name=settings.S3_BUCKET_NAME,
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
