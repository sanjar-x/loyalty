import uuid

from pydantic import BaseModel, ConfigDict, Field


class LogoMetadataRequest(BaseModel):
    filename: str
    content_type: str
    size: int | None = None


class CategoryCreateRequest(BaseModel):
    """Схема входящего запроса на создание категории."""

    name: str = Field(..., min_length=2, max_length=255, examples=["Кроссовки"])
    slug: str = Field(
        ...,
        min_length=3,
        max_length=255,
        pattern=r"^[a-z0-9-]+$",
        examples=["sneakers"],
    )
    parent_id: uuid.UUID | None = Field(
        None, description="ID родительской категории (опционально)"
    )
    sort_order: int = Field(0, description="Порядок сортировки при выводе")


class CategoryCreateResponse(BaseModel):
    """Схема ответа при успешном создании."""

    id: uuid.UUID
    message: str


class CategoryTreeResponse(BaseModel):
    """Схема для вывода категории в дереве (рекурсивная)."""

    id: uuid.UUID
    name: str
    slug: str
    full_slug: str
    level: int
    sort_order: int
    children: list["CategoryTreeResponse"]

    model_config = ConfigDict(from_attributes=True)


class BrandCreateRequest(BaseModel):
    name: str = Field(..., max_length=255)
    slug: str = Field(..., max_length=255)
    logo: LogoMetadataRequest | None = None


class BrandCreateResponse(BaseModel):
    brand_id: uuid.UUID
    presigned_upload_url: str | None = None
    object_key: str | None = None


class ConfirmLogoRequest(BaseModel):
    pass


class BrandResponse(BaseModel):
    """Brand detail response."""

    id: uuid.UUID
    name: str
    slug: str
    logo_url: str | None = None
    logo_status: str | None = None


class BrandUpdateRequest(BaseModel):
    """Partial update request — all fields optional (PATCH semantics)."""

    name: str | None = Field(None, min_length=1, max_length=255)
    slug: str | None = Field(
        None, min_length=1, max_length=255, pattern=r"^[a-z0-9-]+$"
    )


class BrandListResponse(BaseModel):
    """Paginated brand list response."""

    items: list[BrandResponse]
    total: int
    offset: int
    limit: int
