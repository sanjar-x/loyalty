"""Command handler: clear all items from the cart."""

import uuid
from dataclasses import dataclass

from src.modules.cart.application.cart_resolver import find_active_cart_by_owner
from src.modules.cart.domain.interfaces import ICartRepository
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class ClearCartCommand:
    """Input for clearing all items from the cart.

    Attributes:
        identity_id: Authenticated user ID (None for guest).
        anonymous_token: Guest token (None for auth user).
    """

    identity_id: uuid.UUID | None = None
    anonymous_token: str | None = None


class ClearCartHandler:
    """Remove all items from the cart."""

    def __init__(
        self,
        cart_repo: ICartRepository,
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
        self._cart_repo = cart_repo
        self._uow = uow
        self._logger = logger.bind(handler="ClearCartHandler")

    async def handle(self, command: ClearCartCommand) -> None:
        async with self._uow:
            cart = await find_active_cart_by_owner(
                self._cart_repo,
                identity_id=command.identity_id,
                anonymous_token=command.anonymous_token,
            )

            cart.clear()
            await self._cart_repo.update(cart)
            self._uow.register_aggregate(cart)
            await self._uow.commit()
