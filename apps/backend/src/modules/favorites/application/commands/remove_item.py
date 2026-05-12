"""Command: remove a (target_type, target_id) from a favorite list. Idempotent."""

import uuid
from dataclasses import dataclass

from src.modules.favorites.domain.exceptions import (
    FavoriteListNotFoundError,
    FavoriteListNotOwnedError,
)
from src.modules.favorites.domain.interfaces import (
    IFavoriteItemRepository,
    IFavoriteListRepository,
)
from src.modules.favorites.domain.value_objects import FavoriteTargetType
from shared.interfaces.logger import ILogger
from shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class RemoveFavoriteItemCommand:
    identity_id: uuid.UUID
    list_id: uuid.UUID
    target_type: FavoriteTargetType
    target_id: uuid.UUID


@dataclass(frozen=True)
class RemoveFavoriteItemResult:
    removed: bool


class RemoveFavoriteItemHandler:
    def __init__(
        self,
        list_repo: IFavoriteListRepository,
        item_repo: IFavoriteItemRepository,
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
        self._list_repo = list_repo
        self._item_repo = item_repo
        self._uow = uow
        self._logger = logger.bind(handler="RemoveFavoriteItemHandler")

    async def handle(
        self, command: RemoveFavoriteItemCommand
    ) -> RemoveFavoriteItemResult:
        async with self._uow:
            favorite_list = await self._list_repo.get_for_update(command.list_id)
            if favorite_list is None:
                raise FavoriteListNotFoundError(list_id=command.list_id)
            if favorite_list.identity_id != command.identity_id:
                raise FavoriteListNotOwnedError()

            removed = favorite_list.remove_item(
                target_type=command.target_type,
                target_id=command.target_id,
            )
            if not removed:
                # Idempotent no-op — nothing to write, but still commit cleanly
                await self._uow.commit()
                return RemoveFavoriteItemResult(removed=False)

            await self._item_repo.remove(
                list_id=favorite_list.id,
                target_type=command.target_type,
                target_id=command.target_id,
            )
            await self._list_repo.update(favorite_list)
            self._uow.register_aggregate(favorite_list)
            await self._uow.commit()

        return RemoveFavoriteItemResult(removed=True)
