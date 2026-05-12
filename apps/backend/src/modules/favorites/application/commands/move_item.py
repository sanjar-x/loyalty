"""Command: move a (target_type, target_id) between two of the user's lists."""

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
class MoveFavoriteItemCommand:
    identity_id: uuid.UUID
    src_list_id: uuid.UUID
    dst_list_id: uuid.UUID
    target_type: FavoriteTargetType
    target_id: uuid.UUID


class MoveFavoriteItemHandler:
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
        self._logger = logger.bind(handler="MoveFavoriteItemHandler")

    async def handle(self, command: MoveFavoriteItemCommand) -> None:
        if command.src_list_id == command.dst_list_id:
            return

        async with self._uow:
            # Lock in stable order (smaller UUID first) to prevent deadlocks
            first_id, second_id = sorted(
                (command.src_list_id, command.dst_list_id), key=lambda x: str(x)
            )
            first = await self._list_repo.get_for_update(first_id)
            second = await self._list_repo.get_for_update(second_id)

            src = first if first_id == command.src_list_id else second
            dst = second if first_id == command.src_list_id else first

            if src is None:
                raise FavoriteListNotFoundError(list_id=command.src_list_id)
            if dst is None:
                raise FavoriteListNotFoundError(list_id=command.dst_list_id)
            if src.identity_id != command.identity_id:
                raise FavoriteListNotOwnedError()
            if dst.identity_id != command.identity_id:
                raise FavoriteListNotOwnedError()

            removed = src.remove_item(
                target_type=command.target_type,
                target_id=command.target_id,
            )
            if removed:
                await self._item_repo.remove(
                    list_id=src.id,
                    target_type=command.target_type,
                    target_id=command.target_id,
                )
                await self._list_repo.update(src)
                self._uow.register_aggregate(src)

            new_item = dst.add_item(
                target_type=command.target_type,
                target_id=command.target_id,
            )
            if new_item is not None:
                await self._item_repo.add(new_item)
                await self._list_repo.update(dst)
                self._uow.register_aggregate(dst)

            await self._uow.commit()
