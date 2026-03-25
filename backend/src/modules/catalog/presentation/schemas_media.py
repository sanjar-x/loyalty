"""Schemas for media[] array in product create/update payloads."""
from __future__ import annotations

import uuid

from pydantic import field_validator, model_validator

from src.shared.schemas import CamelModel


class ImageVariantItem(CamelModel):
    size: str
    width: int
    height: int
    url: str


class MediaItemRequest(CamelModel):
    url: str
    storage_object_id: uuid.UUID | None = None
    media_type: str = "IMAGE"
    role: str = "GALLERY"
    variant_id: uuid.UUID | None = None
    sort_order: int = 0
    is_external: bool = False
    image_variants: list[ImageVariantItem] | None = None

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        if len(v) > 1024:
            msg = "URL must be <= 1024 characters"
            raise ValueError(msg)
        return v

    @model_validator(mode="after")
    def require_storage_id_for_internal(self):
        if not self.is_external and self.storage_object_id is None:
            msg = "storage_object_id required when is_external=false"
            raise ValueError(msg)
        return self


class MediaItemResponse(CamelModel):
    id: uuid.UUID
    product_id: uuid.UUID
    variant_id: uuid.UUID | None = None
    media_type: str
    role: str
    sort_order: int
    is_external: bool
    storage_object_id: uuid.UUID | None = None
    url: str | None = None
    image_variants: list[ImageVariantItem] | None = None
