"""Command: delete a user-created favorite list (cascades to items)."""

import uuid
from dataclasses import dataclass

from src.modules.favorites.domain.exceptions import (
    FavoriteListNotFoundError,
    FavoriteListNotOwnedError,
)
from src.modules.favorites.domain.interfaces import IFavoriteListRepository
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class DeleteFavoriteListCommand:
    identity_id: uuid.UUID
    list_id: uuid.UUID


class DeleteFavoriteListHandler:
    def __init__(
        self,
        list_repo: IFavoriteListRepository,
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
        self._list_repo = list_repo
        self._uow = uow
        self._logger = logger.bind(handler="DeleteFavoriteListHandler")

    async def handle(self, command: DeleteFavoriteListCommand) -> None:
        async with self._uow:
            favorite_list = await self._list_repo.get_for_update(command.list_id)
            if favorite_list is None:
                raise FavoriteListNotFoundError(list_id=command.list_id)
            if favorite_list.identity_id != command.identity_id:
                raise FavoriteListNotOwnedError()

            favorite_list.mark_deleted()
            self._uow.register_aggregate(favorite_list)
            await self._list_repo.delete(favorite_list.id)
            await self._uow.commit()
