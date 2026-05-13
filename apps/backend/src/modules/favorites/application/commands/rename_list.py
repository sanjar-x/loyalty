"""Command: rename a user-created favorite list."""

import uuid
from dataclasses import dataclass

from src.modules.favorites.domain.exceptions import (
    FavoriteListNameConflictError,
    FavoriteListNotFoundError,
    FavoriteListNotOwnedError,
)
from src.modules.favorites.domain.interfaces import IFavoriteListRepository
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class RenameFavoriteListCommand:
    identity_id: uuid.UUID
    list_id: uuid.UUID
    new_name: str


class RenameFavoriteListHandler:
    def __init__(
        self,
        list_repo: IFavoriteListRepository,
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
        self._list_repo = list_repo
        self._uow = uow
        self._logger = logger.bind(handler="RenameFavoriteListHandler")

    async def handle(self, command: RenameFavoriteListCommand) -> None:
        async with self._uow:
            favorite_list = await self._list_repo.get_for_update(command.list_id)
            if favorite_list is None:
                raise FavoriteListNotFoundError(list_id=command.list_id)
            if favorite_list.identity_id != command.identity_id:
                raise FavoriteListNotOwnedError()

            if (
                favorite_list.name != command.new_name
                and await self._list_repo.name_exists(
                    command.identity_id, command.new_name
                )
            ):
                raise FavoriteListNameConflictError(name=command.new_name)

            favorite_list.rename(command.new_name)
            await self._list_repo.update(favorite_list)
            self._uow.register_aggregate(favorite_list)
            await self._uow.commit()
