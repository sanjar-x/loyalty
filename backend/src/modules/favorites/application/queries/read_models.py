"""Read models exposed by the favorites query handlers."""

import uuid
from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class FavoriteListSummary:
    list_id: uuid.UUID
    name: str
    is_default: bool
    sort_order: int
    item_count: int
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class FavoriteProductCard:
    target_id: uuid.UUID
    slug: str
    title_i18n: dict[str, str]
    main_image_url: str | None


@dataclass(frozen=True)
class FavoriteBrandCard:
    target_id: uuid.UUID
    slug: str
    name: str
    logo_url: str | None


@dataclass(frozen=True)
class FavoriteItemReadModel:
    item_id: uuid.UUID
    list_id: uuid.UUID
    target_type: str
    target_id: uuid.UUID
    added_at: datetime
    product: FavoriteProductCard | None = None
    brand: FavoriteBrandCard | None = None


@dataclass(frozen=True)
class FavoriteItemsPage:
    items: list[FavoriteItemReadModel] = field(default_factory=list)
    next_cursor: str | None = None
