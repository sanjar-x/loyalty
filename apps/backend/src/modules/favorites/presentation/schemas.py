"""Pydantic schemas for the favorites HTTP API."""

import uuid
from datetime import datetime

from pydantic import Field

from src.modules.favorites.domain.entities import MAX_LIST_NAME_LENGTH
from src.modules.favorites.domain.value_objects import FavoriteTargetType
from src.shared.schemas import CamelModel

# ---------------------------------------------------------------------------
# Lists
# ---------------------------------------------------------------------------


class CreateFavoriteListRequest(CamelModel):
    name: str = Field(min_length=1, max_length=MAX_LIST_NAME_LENGTH)


class RenameFavoriteListRequest(CamelModel):
    name: str = Field(min_length=1, max_length=MAX_LIST_NAME_LENGTH)


class FavoriteListResponse(CamelModel):
    id: uuid.UUID
    name: str
    is_default: bool
    sort_order: int
    item_count: int
    created_at: datetime
    updated_at: datetime


class FavoriteListsResponse(CamelModel):
    items: list[FavoriteListResponse]


class CreateFavoriteListResponse(CamelModel):
    id: uuid.UUID


# ---------------------------------------------------------------------------
# Items
# ---------------------------------------------------------------------------


class AddFavoriteItemRequest(CamelModel):
    target_type: FavoriteTargetType
    target_id: uuid.UUID
    list_id: uuid.UUID | None = None


class AddFavoriteItemResponse(CamelModel):
    list_id: uuid.UUID
    item_id: uuid.UUID
    created: bool


class MoveFavoriteItemRequest(CamelModel):
    src_list_id: uuid.UUID
    dst_list_id: uuid.UUID
    target_type: FavoriteTargetType
    target_id: uuid.UUID


class FavoriteProductCardResponse(CamelModel):
    id: uuid.UUID
    slug: str
    title_i18n: dict[str, str]
    main_image_url: str | None = None


class FavoriteBrandCardResponse(CamelModel):
    id: uuid.UUID
    slug: str
    name: str
    logo_url: str | None = None


class FavoriteItemResponse(CamelModel):
    id: uuid.UUID
    list_id: uuid.UUID
    target_type: FavoriteTargetType
    target_id: uuid.UUID
    added_at: datetime
    product: FavoriteProductCardResponse | None = None
    brand: FavoriteBrandCardResponse | None = None


class FavoriteItemsPageResponse(CamelModel):
    items: list[FavoriteItemResponse]
    next_cursor: str | None = None


# ---------------------------------------------------------------------------
# Batch check
# ---------------------------------------------------------------------------


class CheckFavoritedRequest(CamelModel):
    target_type: FavoriteTargetType
    target_ids: list[uuid.UUID] = Field(min_length=1, max_length=200)


class CheckFavoritedResponse(CamelModel):
    """Maps target_id → list_id (str-encoded for JSON object keys)."""

    favorited: dict[str, uuid.UUID]
