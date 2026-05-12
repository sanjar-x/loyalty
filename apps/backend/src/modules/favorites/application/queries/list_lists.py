"""Query: list every favorite list owned by an identity, with item counts."""

import uuid
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.favorites.application.queries.read_models import (
    FavoriteListSummary,
)
from src.modules.favorites.infrastructure.models import (
    FavoriteItemModel,
    FavoriteListModel,
)


@dataclass(frozen=True)
class ListFavoriteListsQuery:
    identity_id: uuid.UUID


class ListFavoriteListsHandler:
    """Direct ORM read (CQRS) — joins the items table for counts."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def handle(self, query: ListFavoriteListsQuery) -> list[FavoriteListSummary]:
        item_count = func.count(FavoriteItemModel.id).label("item_count")
        stmt = (
            select(
                FavoriteListModel.id,
                FavoriteListModel.name,
                FavoriteListModel.is_default,
                FavoriteListModel.sort_order,
                FavoriteListModel.created_at,
                FavoriteListModel.updated_at,
                item_count,
            )
            .outerjoin(
                FavoriteItemModel,
                FavoriteItemModel.list_id == FavoriteListModel.id,
            )
            .where(FavoriteListModel.identity_id == query.identity_id)
            .group_by(FavoriteListModel.id)
            .order_by(
                FavoriteListModel.is_default.desc(),
                FavoriteListModel.sort_order.asc(),
                FavoriteListModel.created_at.asc(),
            )
        )
        result = await self._session.execute(stmt)
        return [
            FavoriteListSummary(
                list_id=row.id,
                name=row.name,
                is_default=row.is_default,
                sort_order=row.sort_order,
                item_count=row.item_count,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            for row in result.all()
        ]
