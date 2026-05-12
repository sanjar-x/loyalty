"""Background service: unfreeze carts whose checkout TTL elapsed (D1.1).

Carts get FROZEN at ``initiate_checkout`` for ``CHECKOUT_TTL_MINUTES = 15``.
If the customer abandons the checkout flow, the cart sits in FROZEN
forever — they can't add new items until the next request hits a lazy
``Cart.is_freeze_expired`` check. UX-wise that means "I left the page
and now my cart is broken".

This canceller runs every 5 minutes (TTL/3 cadence) and unfreezes
expired FROZEN carts proactively. Per-cart isolation: a transient
failure on one cart doesn't poison the batch.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from src.modules.cart.domain.entities import CartStatus
from src.modules.cart.domain.exceptions import CartNotFoundError
from src.modules.cart.domain.interfaces import ICartRepository
from shared.interfaces.logger import ILogger
from shared.interfaces.uow import IUnitOfWork

UNFREEZE_REASON = "freeze_ttl_expired"
"""Sentinel reason string emitted on the ``CartUnfrozenEvent``. Future
analytics consumers can split system-driven unfreezes from explicit
``cancel_checkout`` calls by looking at this value."""


class FreezeExpiryCanceller:
    """One-tick canceller for FROZEN carts past their TTL."""

    def __init__(
        self,
        cart_repo: ICartRepository,
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
        self._cart_repo = cart_repo
        self._uow = uow
        self._logger = logger.bind(service="FreezeExpiryCanceller")

    async def run(self, *, batch_size: int = 100) -> int:
        """Unfreeze every FROZEN cart whose ``frozen_until`` is past.

        Returns the number of carts successfully unfrozen this tick.
        """
        now = datetime.now(UTC)
        # The selector reads outside any UoW context (read-only).
        # Per-cart UoW commits below cleanly isolate failures.
        expired_ids = await self._cart_repo.find_expired_frozen(
            now=now, limit=batch_size
        )
        if not expired_ids:
            return 0

        unfrozen = 0
        for cart_id in expired_ids:
            try:
                if await self._unfreeze_one(cart_id):
                    unfrozen += 1
            except CartNotFoundError:
                # Race: cart deleted between selector and handler.
                self._logger.info(
                    "freeze_expiry.skip", cart_id=str(cart_id), reason="not_found"
                )
            except Exception:
                self._logger.exception(
                    "freeze_expiry.unfreeze_error", cart_id=str(cart_id)
                )

        self._logger.info(
            "freeze_expiry.tick", scanned=len(expired_ids), unfrozen=unfrozen
        )
        return unfrozen

    async def _unfreeze_one(self, cart_id: uuid.UUID) -> bool:
        """Lock + unfreeze one cart inside its own UoW.

        Returns ``True`` on a successful FROZEN→ACTIVE transition + commit;
        ``False`` when the cart is no longer FROZEN (someone else already
        unfroze it — no-op).
        """
        async with self._uow:
            cart = await self._cart_repo.get_for_update(cart_id)
            if cart is None:
                raise CartNotFoundError()
            if cart.status != CartStatus.FROZEN:
                # Concurrent unfreeze (cancel_checkout / next freeze tick)
                # — the selector saw FROZEN, this txn observes a different
                # state. Drop silently; the system is now consistent.
                return False
            cart.unfreeze(UNFREEZE_REASON)
            await self._cart_repo.update(cart)
            self._uow.register_aggregate(cart)
            await self._uow.commit()
        return True
