import uuid

from pydantic import BaseModel, ConfigDict, Field


class CategoryCreateRequest(BaseModel):
    """Схема входящего запроса на создание категории."""

    name: str = Field(..., max_length=255, examples=["Кроссовки"])
    slug: str = Field(
        ..., max_length=255, pattern=r"^[a-z0-9-]+$", examples=["sneakers"]
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
