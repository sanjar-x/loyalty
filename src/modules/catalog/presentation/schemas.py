"""
Pydantic request/response schemas for the Catalog API.

All schemas inherit from :class:`CamelModel` to provide automatic
camelCase ↔ snake_case field aliasing.  These DTOs belong to the
presentation layer and carry no business logic.
"""

import uuid

from pydantic import ConfigDict, Field, model_validator

from src.shared.schemas import CamelModel


class LogoMetadataRequest(CamelModel):
    """Client-supplied metadata for a brand logo upload."""

    filename: str = Field(..., max_length=255)
    content_type: str = Field(..., pattern=r"^image/(jpeg|png|webp|gif|svg\+xml)$")
    size: int | None = None


class CategoryCreateRequest(CamelModel):
    """Request body for creating a new category."""

    name: str = Field(..., min_length=2, max_length=255, examples=["Sneakers"])
    slug: str = Field(
        ...,
        min_length=3,
        max_length=255,
        pattern=r"^[a-z0-9-]+$",
        examples=["sneakers"],
    )
    parent_id: uuid.UUID | None = Field(None, description="Parent category ID (optional)")
    sort_order: int = Field(0, description="Display ordering among siblings")


class CategoryCreateResponse(CamelModel):
    """Response returned after successful category creation."""

    id: uuid.UUID
    message: str


class CategoryTreeResponse(CamelModel):
    """Recursive tree node for the category hierarchy response."""

    id: uuid.UUID
    name: str
    slug: str
    full_slug: str
    level: int
    sort_order: int
    children: list[CategoryTreeResponse]

    model_config = ConfigDict(from_attributes=True)


class CategoryResponse(CamelModel):
    """Single category detail response."""

    id: uuid.UUID
    name: str
    slug: str
    full_slug: str
    level: int
    sort_order: int
    parent_id: uuid.UUID | None = None


class CategoryUpdateRequest(CamelModel):
    """Partial update request — all fields optional (PATCH semantics)."""

    name: str | None = Field(None, min_length=2, max_length=255)
    slug: str | None = Field(None, min_length=3, max_length=255, pattern=r"^[a-z0-9-]+$")
    sort_order: int | None = None

    @model_validator(mode="after")
    def at_least_one_field(self) -> CategoryUpdateRequest:
        if self.name is None and self.slug is None and self.sort_order is None:
            raise ValueError("At least one field (name, slug, or sortOrder) must be provided")
        return self


class CategoryListResponse(CamelModel):
    """Paginated category list response."""

    items: list[CategoryResponse]
    total: int
    offset: int
    limit: int


class BrandCreateRequest(CamelModel):
    """Request body for creating a new brand, with optional logo metadata."""

    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=255, pattern=r"^[a-z0-9-]+$")
    logo: LogoMetadataRequest | None = None


class BrandCreateResponse(CamelModel):
    """Response after brand creation, including an optional presigned upload URL."""

    brand_id: uuid.UUID
    presigned_upload_url: str | None = None
    object_key: str | None = None


class BrandResponse(CamelModel):
    """Brand detail response."""

    id: uuid.UUID
    name: str
    slug: str
    logo_url: str | None = None
    logo_status: str | None = None


class BrandUpdateRequest(CamelModel):
    """Partial update request — all fields optional (PATCH semantics)."""

    name: str | None = Field(None, min_length=1, max_length=255)
    slug: str | None = Field(None, min_length=1, max_length=255, pattern=r"^[a-z0-9-]+$")

    @model_validator(mode="after")
    def at_least_one_field(self) -> BrandUpdateRequest:
        if self.name is None and self.slug is None:
            raise ValueError("At least one field (name or slug) must be provided")
        return self


class BrandListResponse(CamelModel):
    """Paginated brand list response."""

    items: list[BrandResponse]
    total: int
    offset: int
    limit: int
