"""
Command handler: add an item to the cart.

Get-or-create semantics — creates a new cart if the caller has no active one.
If the SKU is already in the cart, quantities are summed (capped at MAX_QTY).
"""

import uuid
from dataclasses import dataclass

from src.modules.cart.domain.entities import Cart
from src.modules.cart.domain.exceptions import SkuNotAvailableError
from src.modules.cart.domain.interfaces import ICartRepository, ISkuReadService
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class AddItemCommand:
    """Input for adding an item to a cart.

    Attributes:
        sku_id: SKU to add.
        quantity: Number of units (1..99).
        identity_id: Authenticated user ID (None for guest).
        anonymous_token: Guest token (None for auth user).
    """

    sku_id: uuid.UUID
    quantity: int
    identity_id: uuid.UUID | None = None
    anonymous_token: str | None = None


@dataclass(frozen=True)
class AddItemResult:
    """Output of add-item command.

    Attributes:
        cart_id: Cart UUID.
        item_id: Cart item UUID.
        quantity: Final item quantity after merge.
    """

    cart_id: uuid.UUID
    item_id: uuid.UUID
    quantity: int


class AddItemHandler:
    """Add an item to a cart (get-or-create)."""

    def __init__(
        self,
        cart_repo: ICartRepository,
        sku_service: ISkuReadService,
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
        self._cart_repo = cart_repo
        self._sku_service = sku_service
        self._uow = uow
        self._logger = logger.bind(handler="AddItemHandler")

    async def handle(self, command: AddItemCommand) -> AddItemResult:
        async with self._uow:
            sku_snapshot = await self._sku_service.get_sku_snapshot(command.sku_id)
            if sku_snapshot is None:
                raise SkuNotAvailableError(sku_id=str(command.sku_id))

            cart = await self._get_or_create_cart(command)
            item = cart.add_item(sku_snapshot, command.quantity)
            await self._cart_repo.update(cart)
            self._uow.register_aggregate(cart)
            await self._uow.commit()

        return AddItemResult(
            cart_id=cart.id,
            item_id=item.id,
            quantity=item.quantity,
        )

    async def _get_or_create_cart(self, command: AddItemCommand) -> Cart:
        if command.identity_id is not None:
            cart = await self._cart_repo.get_active_by_identity(command.identity_id)
        elif command.anonymous_token is not None:
            cart = await self._cart_repo.get_active_by_anonymous(
                command.anonymous_token
            )
        else:
            msg = "Either identity_id or anonymous_token is required"
            raise ValueError(msg)

        if cart is not None:
            return cart

        new_cart = Cart.create(
            identity_id=command.identity_id,
            anonymous_token=command.anonymous_token,
        )
        return await self._cart_repo.add(new_cart)
