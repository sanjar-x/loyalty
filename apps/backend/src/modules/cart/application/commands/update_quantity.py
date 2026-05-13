"""Command handler: update item quantity by SKU."""

import uuid
from dataclasses import dataclass

from src.modules.cart.application.cart_resolver import find_active_cart_by_owner
from src.modules.cart.domain.exceptions import CartItemNotFoundError
from src.modules.cart.domain.interfaces import ICartRepository
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class UpdateQuantityCommand:
    """Input for updating a cart item's quantity.

    Attributes:
        sku_id: SKU whose quantity to update.
        quantity: New quantity (0 removes the item).
        identity_id: Authenticated user ID (None for guest).
        anonymous_token: Guest token (None for auth user).
    """

    sku_id: uuid.UUID
    quantity: int
    identity_id: uuid.UUID | None = None
    anonymous_token: str | None = None


class UpdateQuantityHandler:
    """Update an item's quantity. Quantity of 0 removes the item."""

    def __init__(
        self,
        cart_repo: ICartRepository,
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
        self._cart_repo = cart_repo
        self._uow = uow
        self._logger = logger.bind(handler="UpdateQuantityHandler")

    async def handle(self, command: UpdateQuantityCommand) -> None:
        async with self._uow:
            cart = await find_active_cart_by_owner(
                self._cart_repo,
                identity_id=command.identity_id,
                anonymous_token=command.anonymous_token,
            )

            item = cart.find_item_by_sku(command.sku_id)
            if item is None:
                raise CartItemNotFoundError(item_id=str(command.sku_id))

            cart.update_quantity(item.id, command.quantity)
            await self._cart_repo.update(cart)
            self._uow.register_aggregate(cart)
            await self._uow.commit()
