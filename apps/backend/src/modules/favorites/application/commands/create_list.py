"""Command: create a new (non-default) favorite list for the caller."""

import uuid
from dataclasses import dataclass

from src.modules.favorites.domain.entities import FavoriteList
from src.modules.favorites.domain.exceptions import FavoriteListNameConflictError
from src.modules.favorites.domain.interfaces import IFavoriteListRepository
from shared.interfaces.logger import ILogger
from shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class CreateFavoriteListCommand:
    identity_id: uuid.UUID
    name: str


@dataclass(frozen=True)
class CreateFavoriteListResult:
    list_id: uuid.UUID


class CreateFavoriteListHandler:
    def __init__(
        self,
        list_repo: IFavoriteListRepository,
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
        self._list_repo = list_repo
        self._uow = uow
        self._logger = logger.bind(handler="CreateFavoriteListHandler")

    async def handle(
        self, command: CreateFavoriteListCommand
    ) -> CreateFavoriteListResult:
        async with self._uow:
            if await self._list_repo.name_exists(command.identity_id, command.name):
                raise FavoriteListNameConflictError(name=command.name)

            existing = await self._list_repo.list_by_identity(command.identity_id)
            next_sort_order = max((lst.sort_order for lst in existing), default=0) + 1

            favorite_list = FavoriteList.create(
                identity_id=command.identity_id,
                name=command.name,
                sort_order=next_sort_order,
            )
            await self._list_repo.add(favorite_list)
            self._uow.register_aggregate(favorite_list)
            await self._uow.commit()

        return CreateFavoriteListResult(list_id=favorite_list.id)
