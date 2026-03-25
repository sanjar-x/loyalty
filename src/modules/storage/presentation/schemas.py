"""ImageBackend API schemas — matches spec contract."""
from __future__ import annotations

import uuid
from datetime import datetime

from src.shared.schemas import CamelModel


class UploadRequest(CamelModel):
    content_type: str
    filename: str | None = None


class UploadResponse(CamelModel):
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
    variants: list[MediaVariant] = []
    error: str | None = None


class ExternalImportRequest(CamelModel):
    url: str


class ExternalImportResponse(CamelModel):
    storage_object_id: uuid.UUID
    url: str
    variants: list[MediaVariant] = []


class MetadataResponse(CamelModel):
    storage_object_id: uuid.UUID
    status: str
    url: str | None = None
    content_type: str | None = None
    size_bytes: int = 0
    variants: list[MediaVariant] = []
    created_at: datetime | None = None


class DeleteResponse(CamelModel):
    deleted: bool = True
