"""
Command handler: confirm checkout.

Revalidates prices: price-down → silent update, price-up → unfreeze + error.
On success, marks cart as ORDERED.
"""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from src.modules.cart.domain.exceptions import (
    CartNotFoundError,
    CheckoutPriceChangedError,
    CheckoutSnapshotExpiredError,
    SkuNotAvailableError,
)
from src.modules.cart.domain.interfaces import ICartRepository, ISkuReadService
from src.modules.cart.domain.value_objects import (
    CheckoutItemSnapshot,
    CheckoutSnapshot,
)
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class ConfirmCheckoutCommand:
    """Input for confirming a checkout.

    Attributes:
        identity_id: Authenticated user ID.
        attempt_id: Checkout attempt to confirm.
    """

    identity_id: uuid.UUID
    attempt_id: uuid.UUID


@dataclass(frozen=True)
class ConfirmCheckoutResult:
    """Output of checkout confirmation.

    Attributes:
        order_id: Created order ID, or None if order module not implemented.
        total_amount: Final total in kopecks (may differ from snapshot if price decreased).
        currency: ISO 4217 currency code.
    """

    order_id: uuid.UUID | None
    total_amount: int
    currency: str


class ConfirmCheckoutHandler:
    """Confirm checkout: revalidate prices and mark cart ordered."""

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
        self._logger = logger.bind(handler="ConfirmCheckoutHandler")

    async def handle(self, command: ConfirmCheckoutCommand) -> ConfirmCheckoutResult:
        async with self._uow:
            cart = await self._cart_repo.get_active_or_frozen_by_identity(
                command.identity_id
            )
            if cart is None:
                raise CartNotFoundError(cart_id="unknown")

            attempt = await self._cart_repo.get_pending_checkout_attempt(cart.id)
            if attempt is None or attempt.id != command.attempt_id:
                raise CartNotFoundError(cart_id=str(cart.id))

            snapshot = await self._cart_repo.get_checkout_snapshot(attempt.snapshot_id)
            if snapshot is None:
                raise CartNotFoundError(cart_id=str(cart.id))

            # Check TTL
            now = datetime.now(UTC)
            if now > snapshot.expires_at:
                cart.unfreeze("expired")
                await self._cart_repo.resolve_checkout_attempt(
                    command.attempt_id, status="expired", resolved_at=now
                )
                await self._cart_repo.update(cart)
                self._uow.register_aggregate(cart)
                await self._uow.commit()
                raise CheckoutSnapshotExpiredError()

            # Revalidate prices
            sku_ids = [item.sku_id for item in snapshot.items]
            current_snapshots = await self._sku_service.get_sku_snapshots_batch(sku_ids)

            new_total = 0
            price_changes: dict[str, dict] = {}
            updated_items: list[CheckoutItemSnapshot] = []

            for snap_item in snapshot.items:
                current = current_snapshots.get(snap_item.sku_id)
                if current is None or not current.is_active:
                    # SKU deactivated — unfreeze and error
                    cart.unfreeze("sku_unavailable")
                    await self._cart_repo.resolve_checkout_attempt(
                        command.attempt_id, status="failed", resolved_at=now
                    )
                    await self._cart_repo.update(cart)
                    self._uow.register_aggregate(cart)
                    await self._uow.commit()
                    raise SkuNotAvailableError(sku_id=str(snap_item.sku_id))

                new_line_total = current.price_amount * snap_item.quantity
                new_total += new_line_total

                if current.price_amount != snap_item.unit_price_amount:
                    if current.price_amount > snap_item.unit_price_amount:
                        # Price UP → unfreeze + error
                        cart.unfreeze("price_increased")
                        await self._cart_repo.resolve_checkout_attempt(
                            command.attempt_id, status="failed", resolved_at=now
                        )
                        await self._cart_repo.update(cart)
                        self._uow.register_aggregate(cart)
                        await self._uow.commit()
                        raise CheckoutPriceChangedError(
                            price_diff={
                                str(snap_item.sku_id): {
                                    "old": snap_item.unit_price_amount,
                                    "new": current.price_amount,
                                }
                            }
                        )
                    # Price DOWN → silent update
                    price_changes[str(snap_item.sku_id)] = {
                        "old": snap_item.unit_price_amount,
                        "new": current.price_amount,
                    }

                updated_items.append(
                    CheckoutItemSnapshot(
                        sku_id=snap_item.sku_id,
                        quantity=snap_item.quantity,
                        unit_price_amount=current.price_amount,
                        currency=snap_item.currency,
                    )
                )

            if price_changes:
                self._logger.info(
                    "Price decreased during checkout",
                    cart_id=str(cart.id),
                    changes=price_changes,
                )
                # Persist updated snapshot with decreased prices
                updated_snapshot = CheckoutSnapshot(
                    id=snapshot.id,
                    cart_id=snapshot.cart_id,
                    items=tuple(updated_items),
                    pickup_point_id=snapshot.pickup_point_id,
                    total_amount=new_total,
                    currency=snapshot.currency,
                    created_at=snapshot.created_at,
                    expires_at=snapshot.expires_at,
                )
                await self._cart_repo.update_checkout_snapshot(updated_snapshot)

            # Mark ordered
            cart.mark_ordered()
            await self._cart_repo.resolve_checkout_attempt(
                command.attempt_id, status="confirmed", resolved_at=now
            )
            await self._cart_repo.update(cart)
            self._uow.register_aggregate(cart)
            await self._uow.commit()

        return ConfirmCheckoutResult(
            order_id=None,  # Order module not yet implemented
            total_amount=new_total,
            currency=snapshot.currency,
        )
