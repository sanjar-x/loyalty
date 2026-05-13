"""SQLAlchemy implementation of ``IFavoriteItemRepository``.

This repository writes single ``FavoriteItem`` rows on behalf of the
aggregate; it never side-steps invariants because aggregate-level
``add_item`` / ``remove_item`` is what produces the data passed in.
"""

import uuid

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.favorites.domain.entities import FavoriteItem
from src.modules.favorites.domain.interfaces import IFavoriteItemRepository
from src.modules.favorites.domain.value_objects import FavoriteTargetType
from src.modules.favorites.infrastructure.models import (
    FavoriteItemModel,
    FavoriteListModel,
)


class FavoriteItemRepository(IFavoriteItemRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, item: FavoriteItem) -> None:
        model = FavoriteItemModel(
            id=item.id,
            list_id=item.list_id,
            target_type=item.target_type.value,
            target_id=item.target_id,
            added_at=item.added_at,
        )
        self._session.add(model)
        await self._session.flush()

    async def remove(
        self,
        *,
        list_id: uuid.UUID,
        target_type: FavoriteTargetType,
        target_id: uuid.UUID,
    ) -> bool:
        result = await self._session.execute(
            delete(FavoriteItemModel).where(
                FavoriteItemModel.list_id == list_id,
                FavoriteItemModel.target_type == target_type.value,
                FavoriteItemModel.target_id == target_id,
            )
        )
        return (result.rowcount or 0) > 0

    async def count_by_list(self, list_id: uuid.UUID) -> int:
        stmt = select(func.count(FavoriteItemModel.id)).where(
            FavoriteItemModel.list_id == list_id
        )
        return (await self._session.execute(stmt)).scalar_one()

    async def check_batch(
        self,
        *,
        identity_id: uuid.UUID,
        target_type: FavoriteTargetType,
        target_ids: list[uuid.UUID],
    ) -> dict[uuid.UUID, uuid.UUID]:
        if not target_ids:
            return {}
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
                FavoriteListModel.identity_id == identity_id,
                FavoriteItemModel.target_type == target_type.value,
                FavoriteItemModel.target_id.in_(target_ids),
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
            result.setdefault(row.target_id, row.list_id)
        return result
