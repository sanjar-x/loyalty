"""Query: fetch items in a favorite list with catalog enrichment.

Direct ORM access is the standard pattern for CQRS read-side. Both
``Product`` and ``Brand`` are joined in two short queries (rather than
one polymorphic JOIN) — the per-target_type split keeps the SQL legible
and lets PostgreSQL pick the right index.

Cursor pagination uses ``(added_at DESC, id DESC)`` for stable order.
"""

from __future__ import annotations

import base64
import json
import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.domain.value_objects import MediaRole, ProductStatus
from src.modules.catalog.infrastructure.models import (
    Brand,
    MediaAsset,
    Product,
)
from src.modules.favorites.application.queries.read_models import (
    FavoriteBrandCard,
    FavoriteItemReadModel,
    FavoriteItemsPage,
    FavoriteProductCard,
)
from src.modules.favorites.domain.exceptions import (
    FavoriteListNotFoundError,
    FavoriteListNotOwnedError,
)
from src.modules.favorites.domain.value_objects import FavoriteTargetType
from src.modules.favorites.infrastructure.models import (
    FavoriteItemModel,
    FavoriteListModel,
)

_DEFAULT_PAGE_SIZE = 20
_MAX_PAGE_SIZE = 100


@dataclass(frozen=True)
class GetFavoriteListItemsQuery:
    identity_id: uuid.UUID
    list_id: uuid.UUID
    target_type: FavoriteTargetType | None = None
    cursor: str | None = None
    limit: int = _DEFAULT_PAGE_SIZE


class GetFavoriteListItemsHandler:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def handle(self, query: GetFavoriteListItemsQuery) -> FavoriteItemsPage:
        # Ownership + existence
        list_row = await self._session.execute(
            select(FavoriteListModel.identity_id).where(
                FavoriteListModel.id == query.list_id
            )
        )
        owner_id = list_row.scalar_one_or_none()
        if owner_id is None:
            raise FavoriteListNotFoundError(list_id=query.list_id)
        if owner_id != query.identity_id:
            raise FavoriteListNotOwnedError()

        limit = max(1, min(query.limit, _MAX_PAGE_SIZE))
        cursor_added_at, cursor_id = _decode_cursor(query.cursor)

        stmt = select(
            FavoriteItemModel.id,
            FavoriteItemModel.list_id,
            FavoriteItemModel.target_type,
            FavoriteItemModel.target_id,
            FavoriteItemModel.added_at,
        ).where(FavoriteItemModel.list_id == query.list_id)

        if query.target_type is not None:
            stmt = stmt.where(FavoriteItemModel.target_type == query.target_type.value)

        if cursor_added_at is not None and cursor_id is not None:
            stmt = stmt.where(
                or_(
                    FavoriteItemModel.added_at < cursor_added_at,
                    and_(
                        FavoriteItemModel.added_at == cursor_added_at,
                        FavoriteItemModel.id < cursor_id,
                    ),
                )
            )

        stmt = stmt.order_by(
            FavoriteItemModel.added_at.desc(),
            FavoriteItemModel.id.desc(),
        ).limit(limit + 1)

        rows = (await self._session.execute(stmt)).all()
        has_more = len(rows) > limit
        rows = rows[:limit]

        product_ids = [
            row.target_id
            for row in rows
            if row.target_type == FavoriteTargetType.PRODUCT.value
        ]
        brand_ids = [
            row.target_id
            for row in rows
            if row.target_type == FavoriteTargetType.BRAND.value
        ]

        products = await self._load_products(product_ids)
        brands = await self._load_brands(brand_ids)

        items = [
            FavoriteItemReadModel(
                item_id=row.id,
                list_id=row.list_id,
                target_type=row.target_type,
                target_id=row.target_id,
                added_at=row.added_at,
                product=products.get(row.target_id)
                if row.target_type == FavoriteTargetType.PRODUCT.value
                else None,
                brand=brands.get(row.target_id)
                if row.target_type == FavoriteTargetType.BRAND.value
                else None,
            )
            for row in rows
        ]

        next_cursor = (
            _encode_cursor(rows[-1].added_at, rows[-1].id)
            if has_more and rows
            else None
        )
        return FavoriteItemsPage(items=items, next_cursor=next_cursor)

    async def _load_products(
        self, product_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, FavoriteProductCard]:
        if not product_ids:
            return {}
        stmt = (
            select(
                Product.id,
                Product.slug,
                Product.title_i18n,
                MediaAsset.url.label("main_image_url"),
            )
            .outerjoin(
                MediaAsset,
                and_(
                    MediaAsset.product_id == Product.id,
                    MediaAsset.variant_id.is_(None),
                    MediaAsset.role == MediaRole.MAIN,
                ),
            )
            .where(
                Product.id.in_(product_ids),
                Product.deleted_at.is_(None),
                Product.status == ProductStatus.PUBLISHED,
            )
        )
        result = await self._session.execute(stmt)
        return {
            row.id: FavoriteProductCard(
                target_id=row.id,
                slug=row.slug,
                title_i18n=dict(row.title_i18n or {}),
                main_image_url=row.main_image_url,
            )
            for row in result.all()
        }

    async def _load_brands(
        self, brand_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, FavoriteBrandCard]:
        if not brand_ids:
            return {}
        stmt = select(Brand.id, Brand.slug, Brand.name, Brand.logo_url).where(
            Brand.id.in_(brand_ids)
        )
        result = await self._session.execute(stmt)
        return {
            row.id: FavoriteBrandCard(
                target_id=row.id,
                slug=row.slug,
                name=row.name,
                logo_url=row.logo_url,
            )
            for row in result.all()
        }


def _encode_cursor(added_at: datetime, item_id: uuid.UUID) -> str:
    payload = json.dumps({"a": added_at.isoformat(), "i": str(item_id)})
    return base64.urlsafe_b64encode(payload.encode()).decode()


def _decode_cursor(
    cursor: str | None,
) -> tuple[datetime | None, uuid.UUID | None]:
    if not cursor:
        return None, None
    try:
        payload = json.loads(base64.urlsafe_b64decode(cursor.encode()).decode())
        return datetime.fromisoformat(payload["a"]), uuid.UUID(payload["i"])
    except ValueError, KeyError:
        return None, None
