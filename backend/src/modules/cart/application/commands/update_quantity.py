"""Command handler: update item quantity by SKU."""

import uuid
from dataclasses import dataclass

from src.modules.cart.domain.entities import Cart
from src.modules.cart.domain.exceptions import CartItemNotFoundError, CartNotFoundError
from src.modules.cart.domain.interfaces import ICartRepository
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class UpdateQuantityCommand:
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
            cart = await self._find_cart_by_owner(command)

            item = cart.find_item_by_sku(command.sku_id)
            if item is None:
                raise CartItemNotFoundError(item_id=str(command.sku_id))

            cart.update_quantity(item.id, command.quantity)
            await self._cart_repo.update(cart)
            self._uow.register_aggregate(cart)
            await self._uow.commit()

    async def _find_cart_by_owner(self, command: UpdateQuantityCommand) -> Cart:
        if command.identity_id is not None:
            cart = await self._cart_repo.get_active_by_identity(command.identity_id)
        elif command.anonymous_token is not None:
            cart = await self._cart_repo.get_active_by_anonymous(
                command.anonymous_token
            )
        else:
            msg = "Either identity_id or anonymous_token is required"
            raise ValueError(msg)
        if cart is None:
            raise CartNotFoundError(cart_id="unknown")
        return cart
