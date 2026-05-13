"""Query: batch-check whether a set of target_ids is favorited by the user.

Used by storefront PLP/PDP to render the heart icon on every product
or brand card after the page loads. The default list takes priority
when a target appears in multiple lists.
"""

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.favorites.domain.value_objects import FavoriteTargetType
from src.modules.favorites.infrastructure.models import (
    FavoriteItemModel,
    FavoriteListModel,
)


@dataclass(frozen=True)
class CheckFavoritedBatchQuery:
    identity_id: uuid.UUID
    target_type: FavoriteTargetType
    target_ids: list[uuid.UUID]


class CheckFavoritedBatchHandler:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def handle(
        self, query: CheckFavoritedBatchQuery
    ) -> dict[uuid.UUID, uuid.UUID]:
        if not query.target_ids:
            return {}

        # Default list first, then by sort_order — the priority for the
        # "which list is this in?" answer when a target appears in many.
        stmt = (
            select(
                FavoriteItemModel.target_id,
                FavoriteItemModel.list_id,
            )
            .join(
                FavoriteListModel,
                FavoriteListModel.id == FavoriteItemModel.list_id,
            )
            .where(
                FavoriteListModel.identity_id == query.identity_id,
                FavoriteItemModel.target_type == query.target_type.value,
                FavoriteItemModel.target_id.in_(query.target_ids),
            )
            .order_by(
                FavoriteListModel.is_default.desc(),
                FavoriteListModel.sort_order.asc(),
                FavoriteListModel.created_at.asc(),
            )
        )
        rows = (await self._session.execute(stmt)).all()

        result: dict[uuid.UUID, uuid.UUID] = {}
        for row in rows:
            # First row wins thanks to the ORDER BY above
            result.setdefault(row.target_id, row.list_id)
        return result
