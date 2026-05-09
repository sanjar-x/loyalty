"""Image module API schemas.

Ported from image_backend's ``modules/storage/presentation/schemas.py``.
``CamelModel`` base is reused from main backend's shared schemas.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import Field

from src.shared.schemas import CamelModel


class UploadRequest(CamelModel):
    content_type: str
    filename: str | None = None


class UploadResponse(CamelModel):
    storage_object_id: uuid.UUID
    presigned_url: str
    expires_in: int = 300


class ReuploadRequest(CamelModel):
    content_type: str
    filename: str | None = None


class ReuploadResponse(CamelModel):
    storage_object_id: uuid.UUID
    presigned_url: str
    expires_in: int = 300


class ConfirmResponse(CamelModel):
    storage_object_id: uuid.UUID
    status: str = "processing"


class MediaVariant(CamelModel):
    size: str
    width: int
    height: int
    url: str


class StatusEventData(CamelModel):
    status: str
    storage_object_id: uuid.UUID
    url: str | None = None
    variants: list[MediaVariant] = Field(default_factory=list)
    error: str | None = None


class ExternalImportRequest(CamelModel):
    url: str


class ExternalImportResponse(CamelModel):
    storage_object_id: uuid.UUID
    url: str
    variants: list[MediaVariant] = Field(default_factory=list)


class MetadataResponse(CamelModel):
    storage_object_id: uuid.UUID
    status: str
    url: str | None = None
    content_type: str | None = None
    size_bytes: int = 0
    variants: list[MediaVariant] = Field(default_factory=list)
    created_at: datetime | None = None


class DeleteResponse(CamelModel):
    deleted: bool = True


class RemoveBackgroundResponse(CamelModel):
    """202 response for ``POST /admin/media/{id}/remove-background`` (IMG-007).

    The ``derived_storage_object_id`` is what the admin UI subscribes
    to via the existing ``GET /admin/media/{id}/status`` SSE channel.

    ``status``:
        - ``processing`` — work was queued (or was already running on
          a prior call). Listen on SSE for the ``completed`` /
          ``failed`` event.
        - ``completed`` — a derivation already exists; ``url`` is
          populated and no SSE subscription is needed.

    ``alreadyExisted`` distinguishes "instant return" (idempotent
    re-call) from "we just queued work" so the UI can skip a spinner
    when nothing was kicked off.
    """

    derived_storage_object_id: uuid.UUID
    status: str  # "processing" | "completed"
    url: str | None = None
    already_existed: bool
