"""Image module admin router (staff-only).

  POST   /admin/media/upload                       reserve slot, return presigned PUT URL
  POST   /admin/media/{id}/reupload                replace image, keep same ID & URLs
  POST   /admin/media/{id}/confirm                 verify S3, dispatch processing
  GET    /admin/media/{id}/status                  SSE stream for processing status
  GET    /admin/media/{id}                          get metadata
  DELETE /admin/media/{id}                          delete files + record
  POST   /admin/media/external                     import from external URL
  POST   /admin/media/{id}/remove-background       kick off Bria RMBG-2.0 cutout (IMG-007)

Auth: staff JWT + ``RequirePermission("media:manage")`` per route. Replaces
the X-API-Key model used by the legacy ``image_backend`` microservice
(CEO directive 2026-05-08, β: full JWT migration).

IMG-001 — pulled the upload / reupload / confirm / external-import
business logic out of the route bodies into proper application
commands so the router only handles HTTP framing + auth.
"""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import AsyncIterable

import structlog
from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Depends, status
from fastapi.sse import EventSourceResponse, ServerSentEvent
from redis.exceptions import RedisError
from sqlalchemy.ext.asyncio import AsyncSession

from src.bootstrap.config import Settings
from src.modules.identity.presentation.dependencies import RequirePermission
from src.modules.image.application.commands.confirm_upload import (
    ConfirmUploadCommand,
    ConfirmUploadHandler,
)
from src.modules.image.application.commands.delete_storage_object import (
    DeleteStorageObjectHandler,
)
from src.modules.image.application.commands.import_external import (
    ImportExternalCommand,
    ImportExternalHandler,
    _VariantUpload,
)
from src.modules.image.application.commands.request_background_removal import (
    RequestBackgroundRemovalCommand,
    RequestBackgroundRemovalHandler,
)
from src.modules.image.application.commands.request_upload import (
    RequestUploadCommand,
    RequestUploadHandler,
)
from src.modules.image.application.commands.reupload import (
    ReuploadCommand,
    ReuploadHandler,
)
from src.modules.image.domain.exceptions import StorageFileNotFoundError
from src.modules.image.domain.interfaces import IStorageRepository
from src.modules.image.infrastructure.services.image_processor import build_variants
from src.modules.image.infrastructure.services.sse_manager import SSEManager
from src.modules.image.infrastructure.tasks import (
    process_image_task,
    remove_background_task,
)
from src.modules.image.presentation.schemas import (
    ConfirmResponse,
    DeleteResponse,
    ExternalImportRequest,
    ExternalImportResponse,
    MediaVariant,
    MetadataResponse,
    RemoveBackgroundResponse,
    ReuploadRequest,
    ReuploadResponse,
    StatusEventData,
    UploadRequest,
    UploadResponse,
)
from src.modules.image.presentation.validators import (
    secure_external_fetch,
    validate_image_content_type,
)

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
    handler: FromDishka[RequestUploadHandler],
    settings: FromDishka[Settings],
) -> UploadResponse:
    validate_image_content_type(body.content_type)
    result = await handler.handle(
        RequestUploadCommand(
            content_type=body.content_type,
            filename=body.filename,
            bucket_name=settings.S3_BUCKET_NAME,
            presigned_url_ttl=settings.MEDIA_PRESIGNED_URL_TTL,
        )
    )
    return UploadResponse(
        storage_object_id=result.storage_object_id,
        presigned_url=result.presigned_url,
        expires_in=result.expires_in,
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
    handler: FromDishka[ReuploadHandler],
    settings: FromDishka[Settings],
) -> ReuploadResponse:
    validate_image_content_type(body.content_type)
    result = await handler.handle(
        ReuploadCommand(
            storage_object_id=storage_object_id,
            content_type=body.content_type,
            filename=body.filename,
            presigned_url_ttl=settings.MEDIA_PRESIGNED_URL_TTL,
        )
    )
    return ReuploadResponse(
        storage_object_id=result.storage_object_id,
        presigned_url=result.presigned_url,
        expires_in=result.expires_in,
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
    handler: FromDishka[ConfirmUploadHandler],
    settings: FromDishka[Settings],
) -> ConfirmResponse:
    await handler.handle(
        ConfirmUploadCommand(
            storage_object_id=storage_object_id,
            max_file_size=settings.MEDIA_MAX_FILE_SIZE,
        )
    )
    # Variant-generation kicked HERE so the worker observes a
    # committed PROCESSING row. ``process_image_task`` is infrastructure
    # — invoking it from the application command would violate Rule 3.
    await process_image_task.kiq(  # ty:ignore[no-matching-overload]
        str(storage_object_id)
    )
    return ConfirmResponse(storage_object_id=storage_object_id)


# ---------------------------------------------------------------------------
# 4. GET /{storage_object_id}/status — SSE stream for processing status
# ---------------------------------------------------------------------------
@media_admin_router.get(
    "/{storage_object_id}/status",
    response_class=EventSourceResponse,
    # ``AsyncIterable[ServerSentEvent]`` return annotation is a forward
    # reference Pydantic cannot resolve for OpenAPI schema generation —
    # crashes ``GET /openapi.json``. Skip response-schema introspection
    # for this stream route (CAT-007).
    response_model=None,
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

    try:
        async for event in sse_manager.subscribe(storage_object_id):
            if event is None:
                continue
            yield ServerSentEvent(data=event, event="status")
            if event.get("status") in ("completed", "failed"):
                return
    except RedisError, OSError:
        # Pub/sub backbone went down mid-stream — emit an explicit
        # ``error`` SSE frame so the client knows it should reconnect
        # rather than silently rendering a stale state.
        logger.exception(
            "sse_status_stream_pubsub_unavailable",
            storage_object_id=str(storage_object_id),
        )
        yield ServerSentEvent(
            data={"reason": "pubsub_unavailable"},
            event="error",
        )


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
        storage_object_id=storage_object_id,
        url=storage_file.url,
        content_type=storage_file.content_type,
        size_bytes=storage_file.size_bytes,
        status=storage_file.status.value,
        variants=[MediaVariant(**v) for v in (storage_file.image_variants or [])],
    )


# ---------------------------------------------------------------------------
# 6. DELETE /{storage_object_id} — Delete media + S3 keys
# ---------------------------------------------------------------------------
@media_admin_router.delete(
    "/{storage_object_id}",
    response_model=DeleteResponse,
    summary="Delete media (S3 + DB record)",
    dependencies=[Depends(RequirePermission(codename=_MEDIA_PERMISSION))],
)
async def delete_media(
    storage_object_id: uuid.UUID,
    handler: FromDishka[DeleteStorageObjectHandler],
) -> DeleteResponse:
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
    handler: FromDishka[ImportExternalHandler],
    settings: FromDishka[Settings],
) -> ExternalImportResponse:
    log = logger.bind(external_url=body.url)
    log.info("External import started")

    # IMG-002 — single helper handles SSRF (redirect re-validation +
    # IP pinning) AND streamed-with-size-cap download. Replaces the
    # prior ``validate_external_url`` + ``httpx.get(follow_redirects=True)``
    # + ``len(response.content)`` combo that left both the redirect
    # bypass and the memory-exhaustion DoS open.
    raw_data = await secure_external_fetch(
        body.url,
        max_size_bytes=settings.MEDIA_MAX_FILE_SIZE,
    )

    sid = uuid.uuid7() if hasattr(uuid, "uuid7") else uuid.uuid4()

    main_bytes, variants_meta, variants_data = await asyncio.to_thread(
        build_variants, raw_data, sid, settings.S3_PUBLIC_BASE_URL
    )

    main_key = f"public/{sid}.webp"
    public_url = f"{settings.S3_PUBLIC_BASE_URL.rstrip('/')}/{main_key}"
    filename = body.url.split("/")[-1].split("?")[0]

    result = await handler.handle(
        ImportExternalCommand(
            storage_object_id=sid,
            bucket_name=settings.S3_BUCKET_NAME,
            main_key=main_key,
            main_bytes=main_bytes,
            variants_data=tuple(
                _VariantUpload(s3_key=k, data=d) for k, d in variants_data.items()
            ),
            variants_meta=variants_meta,
            public_url=public_url,
            filename=filename,
            source_url=body.url,
        )
    )

    return ExternalImportResponse(
        storage_object_id=result.storage_object_id,
        url=result.public_url,
        variants=[MediaVariant(**v) for v in result.variants_meta],
    )


# ---------------------------------------------------------------------------
# 8. POST /{id}/remove-background — kick off Bria RMBG-2.0 cutout (IMG-007)
# ---------------------------------------------------------------------------
@media_admin_router.post(
    "/{storage_object_id}/remove-background",
    response_model=RemoveBackgroundResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Request a background-removal derivation",
    description=(
        "Provisions a derived StorageObject with a parent link and "
        "dispatches the Bria RMBG-2.0 inference task on the "
        "``image_ml`` worker. Idempotent: a second call returns the "
        "existing derivation without re-running inference. Subscribe "
        "to ``GET /admin/media/{derived_storage_object_id}/status`` "
        "for SSE updates."
    ),
    dependencies=[Depends(RequirePermission(codename=_MEDIA_PERMISSION))],
)
async def request_background_removal(
    storage_object_id: uuid.UUID,
    handler: FromDishka[RequestBackgroundRemovalHandler],
) -> RemoveBackgroundResponse:
    result = await handler.handle(
        RequestBackgroundRemovalCommand(parent_storage_object_id=storage_object_id)
    )
    # Dispatch only when we just provisioned a fresh PROCESSING row.
    # The idempotent path (``already_existed=True``) returns the
    # existing derivation untouched; firing the task again would
    # re-run inference for nothing.
    if not result.already_existed and result.status == "PROCESSING":
        await remove_background_task.kiq(  # ty:ignore[no-matching-overload]
            derived_storage_object_id=str(result.derived_storage_object_id),
        )
    return RemoveBackgroundResponse(
        derived_storage_object_id=result.derived_storage_object_id,
        status="completed" if result.status == "COMPLETED" else "processing",
        url=result.url,
        already_existed=result.already_existed,
    )
