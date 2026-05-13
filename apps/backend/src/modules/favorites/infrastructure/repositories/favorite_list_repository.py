"""SQLAlchemy implementation of ``IFavoriteListRepository``.

Maps between ``FavoriteListModel``/``FavoriteItemModel`` ORM rows and
the ``FavoriteList`` domain aggregate using the Data Mapper pattern.
"""

import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.modules.favorites.domain.entities import FavoriteItem, FavoriteList
from src.modules.favorites.domain.interfaces import IFavoriteListRepository
from src.modules.favorites.domain.value_objects import FavoriteTargetType
from src.modules.favorites.infrastructure.models import (
    FavoriteListModel,
)


class FavoriteListRepository(IFavoriteListRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # Mapping helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _to_domain(model: FavoriteListModel) -> FavoriteList:
        items = [
            FavoriteItem(
                id=item.id,
                list_id=item.list_id,
                target_type=FavoriteTargetType(item.target_type),
                target_id=item.target_id,
                added_at=item.added_at,
            )
            for item in model.items
        ]
        favorite_list = FavoriteList(
            id=model.id,
            identity_id=model.identity_id,
            name=model.name,
            is_default=model.is_default,
            sort_order=model.sort_order,
            created_at=model.created_at,
            updated_at=model.updated_at,
            items=items,
        )
        favorite_list.clear_domain_events()
        return favorite_list

    @staticmethod
    def _apply_to_orm(domain: FavoriteList, model: FavoriteListModel) -> None:
        model.identity_id = domain.identity_id
        model.name = domain.name
        model.is_default = domain.is_default
        model.sort_order = domain.sort_order
        model.created_at = domain.created_at
        model.updated_at = domain.updated_at

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    async def add(self, favorite_list: FavoriteList) -> FavoriteList:
        model = FavoriteListModel(id=favorite_list.id)
        self._apply_to_orm(favorite_list, model)
        # Items are written separately by IFavoriteItemRepository.add to
        # keep idempotent paths simple. New aggregates start with empty
        # items so we don't sync them here.
        self._session.add(model)
        await self._session.flush()
        favorite_list.clear_domain_events()
        return favorite_list

    async def get(self, list_id: uuid.UUID) -> FavoriteList | None:
        stmt = (
            select(FavoriteListModel)
            .where(FavoriteListModel.id == list_id)
            .options(selectinload(FavoriteListModel.items))
        )
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def get_for_update(self, list_id: uuid.UUID) -> FavoriteList | None:
        stmt = (
            select(FavoriteListModel)
            .where(FavoriteListModel.id == list_id)
            .options(selectinload(FavoriteListModel.items))
            .with_for_update()
        )
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def get_default_for_identity(
        self, identity_id: uuid.UUID
    ) -> FavoriteList | None:
        stmt = (
            select(FavoriteListModel)
            .where(
                FavoriteListModel.identity_id == identity_id,
                FavoriteListModel.is_default.is_(True),
            )
            .options(selectinload(FavoriteListModel.items))
            .with_for_update()
        )
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def list_by_identity(self, identity_id: uuid.UUID) -> list[FavoriteList]:
        stmt = (
            select(FavoriteListModel)
            .where(FavoriteListModel.identity_id == identity_id)
            .options(selectinload(FavoriteListModel.items))
            .order_by(
                FavoriteListModel.is_default.desc(),
                FavoriteListModel.sort_order.asc(),
                FavoriteListModel.created_at.asc(),
            )
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return [self._to_domain(row) for row in rows]

    async def update(self, favorite_list: FavoriteList) -> None:
        model = await self._session.get(FavoriteListModel, favorite_list.id)
        if model is None:
            # Caller should have loaded via get_for_update — defensive only
            return
        self._apply_to_orm(favorite_list, model)
        await self._session.flush()

    async def delete(self, list_id: uuid.UUID) -> None:
        # CASCADE on FK removes items automatically.
        await self._session.execute(
            delete(FavoriteListModel).where(FavoriteListModel.id == list_id)
        )

    async def name_exists(self, identity_id: uuid.UUID, name: str) -> bool:
        stmt = select(FavoriteListModel.id).where(
            FavoriteListModel.identity_id == identity_id,
            FavoriteListModel.name == name.strip(),
        )
        return (await self._session.execute(stmt)).first() is not None
