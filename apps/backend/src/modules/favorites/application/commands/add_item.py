"""Command: add a (target_type, target_id) to a favorite list.

If ``list_id`` is not supplied the handler resolves (or lazily creates)
the user's default ``Избранное`` list and writes there. The catalog
target validator is invoked first, so non-existent / unpublished
products / soft-deleted brands are rejected with 422 instead of being
saved.
"""

import uuid
from dataclasses import dataclass

from src.modules.favorites.domain.entities import FavoriteList
from src.modules.favorites.domain.exceptions import (
    FavoriteListNotFoundError,
    FavoriteListNotOwnedError,
    FavoriteTargetInvalidError,
)
from src.modules.favorites.domain.interfaces import (
    IFavoriteItemRepository,
    IFavoriteListRepository,
    IFavoriteTargetValidator,
)
from src.modules.favorites.domain.value_objects import FavoriteTargetType
from shared.interfaces.logger import ILogger
from shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class AddFavoriteItemCommand:
    identity_id: uuid.UUID
    target_type: FavoriteTargetType
    target_id: uuid.UUID
    list_id: uuid.UUID | None = None


@dataclass(frozen=True)
class AddFavoriteItemResult:
    list_id: uuid.UUID
    item_id: uuid.UUID
    created: bool


class AddFavoriteItemHandler:
    def __init__(
        self,
        list_repo: IFavoriteListRepository,
        item_repo: IFavoriteItemRepository,
        target_validator: IFavoriteTargetValidator,
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
        self._list_repo = list_repo
        self._item_repo = item_repo
        self._target_validator = target_validator
        self._uow = uow
        self._logger = logger.bind(handler="AddFavoriteItemHandler")

    async def handle(self, command: AddFavoriteItemCommand) -> AddFavoriteItemResult:
        check = await self._target_validator.check(
            target_type=command.target_type,
            target_id=command.target_id,
        )
        if not check.exists:
            raise FavoriteTargetInvalidError(
                target_type=command.target_type.value,
                target_id=command.target_id,
                reason=check.reason or "not_found",
            )

        async with self._uow:
            favorite_list = await self._resolve_list(command)

            existing = favorite_list.find_item(command.target_type, command.target_id)
            if existing is not None:
                # Idempotent path — no event, no INSERT
                return AddFavoriteItemResult(
                    list_id=favorite_list.id,
                    item_id=existing.id,
                    created=False,
                )

            item = favorite_list.add_item(
                target_type=command.target_type,
                target_id=command.target_id,
            )
            assert item is not None  # find_item was None above
            await self._item_repo.add(item)
            await self._list_repo.update(favorite_list)
            self._uow.register_aggregate(favorite_list)
            await self._uow.commit()

        return AddFavoriteItemResult(
            list_id=favorite_list.id,
            item_id=item.id,
            created=True,
        )

    async def _resolve_list(self, command: AddFavoriteItemCommand) -> FavoriteList:
        if command.list_id is not None:
            favorite_list = await self._list_repo.get_for_update(command.list_id)
            if favorite_list is None:
                raise FavoriteListNotFoundError(list_id=command.list_id)
            if favorite_list.identity_id != command.identity_id:
                raise FavoriteListNotOwnedError()
            return favorite_list

        # Lazy default-list creation on first write
        default = await self._list_repo.get_default_for_identity(command.identity_id)
        if default is not None:
            return default

        new_default = FavoriteList.create_default(command.identity_id)
        return await self._list_repo.add(new_default)
