"""Command handler: remove an item from the cart by SKU."""

import uuid
from dataclasses import dataclass

from src.modules.cart.application.cart_resolver import find_active_cart_by_owner
from src.modules.cart.domain.exceptions import CartItemNotFoundError
from src.modules.cart.domain.interfaces import ICartRepository
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class RemoveItemCommand:
    """Input for removing an item from the cart.

    Attributes:
        sku_id: SKU to remove.
        identity_id: Authenticated user ID (None for guest).
        anonymous_token: Guest token (None for auth user).
    """

    sku_id: uuid.UUID
    identity_id: uuid.UUID | None = None
    anonymous_token: str | None = None


class RemoveItemHandler:
    """Remove an item from the cart by SKU ID."""

    def __init__(
        self,
        cart_repo: ICartRepository,
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
        self._cart_repo = cart_repo
        self._uow = uow
        self._logger = logger.bind(handler="RemoveItemHandler")

    async def handle(self, command: RemoveItemCommand) -> None:
        async with self._uow:
            cart = await find_active_cart_by_owner(
                self._cart_repo,
                identity_id=command.identity_id,
                anonymous_token=command.anonymous_token,
            )

            item = cart.find_item_by_sku(command.sku_id)
            if item is None:
                raise CartItemNotFoundError(item_id=str(command.sku_id))

            cart.remove_item(item.id)
            await self._cart_repo.update(cart)
            self._uow.register_aggregate(cart)
            await self._uow.commit()
