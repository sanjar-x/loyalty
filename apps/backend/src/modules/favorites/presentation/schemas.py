"""Pydantic schemas for the favorites HTTP API."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from src.modules.favorites.domain.entities import MAX_LIST_NAME_LENGTH
from src.modules.favorites.domain.value_objects import FavoriteTargetType

# ---------------------------------------------------------------------------
# Lists
# ---------------------------------------------------------------------------


class CreateFavoriteListRequest(BaseModel):
    name: str = Field(min_length=1, max_length=MAX_LIST_NAME_LENGTH)


class RenameFavoriteListRequest(BaseModel):
    name: str = Field(min_length=1, max_length=MAX_LIST_NAME_LENGTH)


class FavoriteListResponse(BaseModel):
    id: uuid.UUID
    name: str
    is_default: bool
    sort_order: int
    item_count: int
    created_at: datetime
    updated_at: datetime


class FavoriteListsResponse(BaseModel):
    items: list[FavoriteListResponse]


class CreateFavoriteListResponse(BaseModel):
    id: uuid.UUID


# ---------------------------------------------------------------------------
# Items
# ---------------------------------------------------------------------------


class AddFavoriteItemRequest(BaseModel):
    target_type: FavoriteTargetType
    target_id: uuid.UUID
    list_id: uuid.UUID | None = None


class AddFavoriteItemResponse(BaseModel):
    list_id: uuid.UUID
    item_id: uuid.UUID
    created: bool


class MoveFavoriteItemRequest(BaseModel):
    src_list_id: uuid.UUID
    dst_list_id: uuid.UUID
    target_type: FavoriteTargetType
    target_id: uuid.UUID


class FavoriteProductCardResponse(BaseModel):
    id: uuid.UUID
    slug: str
    title_i18n: dict[str, str]
    main_image_url: str | None = None


class FavoriteBrandCardResponse(BaseModel):
    id: uuid.UUID
    slug: str
    name: str
    logo_url: str | None = None


class FavoriteItemResponse(BaseModel):
    id: uuid.UUID
    list_id: uuid.UUID
    target_type: FavoriteTargetType
    target_id: uuid.UUID
    added_at: datetime
    product: FavoriteProductCardResponse | None = None
    brand: FavoriteBrandCardResponse | None = None


class FavoriteItemsPageResponse(BaseModel):
    items: list[FavoriteItemResponse]
    next_cursor: str | None = None


# ---------------------------------------------------------------------------
# Batch check
# ---------------------------------------------------------------------------


class CheckFavoritedRequest(BaseModel):
    target_type: FavoriteTargetType
    target_ids: list[uuid.UUID] = Field(min_length=1, max_length=200)


class CheckFavoritedResponse(BaseModel):
    """Maps target_id → list_id (str-encoded for JSON object keys)."""

    favorited: dict[str, uuid.UUID]
