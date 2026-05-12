"""Command handler: cancel checkout and unfreeze the cart."""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from src.modules.cart.domain.exceptions import CartNotFoundError
from src.modules.cart.domain.interfaces import ICartRepository
from src.modules.cart.domain.value_objects import CheckoutAttemptStatus
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class CancelCheckoutCommand:
    """Input for cancelling a pending checkout.

    Attributes:
        identity_id: Authenticated user ID.
    """

    identity_id: uuid.UUID


class CancelCheckoutHandler:
    """Cancel a pending checkout and unfreeze the cart."""

    def __init__(
        self,
        cart_repo: ICartRepository,
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
        self._cart_repo = cart_repo
        self._uow = uow
        self._logger = logger.bind(handler="CancelCheckoutHandler")

    async def handle(self, command: CancelCheckoutCommand) -> None:
        async with self._uow:
            cart = await self._cart_repo.get_active_or_frozen_by_identity(
                command.identity_id
            )
            if cart is None:
                raise CartNotFoundError()

            attempt = await self._cart_repo.get_pending_checkout_attempt(cart.id)
            if attempt is None:
                raise CartNotFoundError()

            now = datetime.now(UTC)
            cart.unfreeze("cancelled")
            await self._cart_repo.resolve_checkout_attempt(
                attempt.id,
                status=CheckoutAttemptStatus.CANCELLED.value,
                resolved_at=now,
            )
            await self._cart_repo.update(cart)
            self._uow.register_aggregate(cart)
            await self._uow.commit()
