"""
Command handler: initiate checkout.

SELECT FOR UPDATE the cart, validate all SKUs, freeze the cart,
create a price snapshot and a checkout attempt record.
"""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from src.modules.cart.application.constants import (
    CHECKOUT_TTL_MINUTES,
    DEFAULT_CURRENCY,
)
from src.modules.cart.domain.exceptions import (
    CartEmptyError,
    CartNotFoundError,
    DuplicateCheckoutAttemptError,
    SkuNotAvailableError,
)
from src.modules.cart.domain.interfaces import (
    ICartRepository,
    IPickupPointReadService,
    ISkuReadService,
)
from src.modules.cart.domain.value_objects import CheckoutItemSnapshot, CheckoutSnapshot
from src.shared.exceptions import ValidationError
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class InitiateCheckoutCommand:
    """Input for initiating a checkout.

    Attributes:
        identity_id: Authenticated user ID.
        pickup_point_id: Selected pickup point.
    """

    identity_id: uuid.UUID
    pickup_point_id: uuid.UUID


@dataclass(frozen=True)
class InitiateCheckoutResult:
    """Output of checkout initiation.

    Attributes:
        snapshot_id: Created price snapshot ID.
        attempt_id: Created checkout attempt ID.
        expires_at: When the snapshot expires.
        total_amount: Grand total in kopecks.
        currency: ISO 4217 currency code.
    """

    snapshot_id: uuid.UUID
    attempt_id: uuid.UUID
    expires_at: datetime
    total_amount: int
    currency: str


class InitiateCheckoutHandler:
    """Freeze the cart and create a checkout snapshot."""

    def __init__(
        self,
        cart_repo: ICartRepository,
        sku_service: ISkuReadService,
        pickup_service: IPickupPointReadService,
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
        self._cart_repo = cart_repo
        self._sku_service = sku_service
        self._pickup_service = pickup_service
        self._uow = uow
        self._logger = logger.bind(handler="InitiateCheckoutHandler")

    async def handle(self, command: InitiateCheckoutCommand) -> InitiateCheckoutResult:
        async with self._uow:
            cart = await self._cart_repo.get_active_by_identity_for_update(
                command.identity_id
            )
            if cart is None:
                raise CartNotFoundError()

            if not cart.items:
                raise CartEmptyError()

            # Check for existing pending attempt
            pending = await self._cart_repo.get_pending_checkout_attempt(cart.id)
            if pending is not None:
                raise DuplicateCheckoutAttemptError()

            # Validate pickup point
            if not await self._pickup_service.exists(command.pickup_point_id):
                raise ValidationError(
                    message=f"Pickup point not found: {command.pickup_point_id}",
                    error_code="PICKUP_POINT_NOT_FOUND",
                )

            # Batch-load SKU snapshots
            sku_ids = [item.sku_id for item in cart.items]
            snapshots = await self._sku_service.get_sku_snapshots_batch(sku_ids)

            # Validate all SKUs active
            checkout_items: list[CheckoutItemSnapshot] = []
            total_amount = 0
            currency = DEFAULT_CURRENCY

            for item in cart.items:
                sku_snapshot = snapshots.get(item.sku_id)
                if sku_snapshot is None or not sku_snapshot.is_active:
                    raise SkuNotAvailableError(sku_id=str(item.sku_id))
                line_total = sku_snapshot.price_amount * item.quantity
                total_amount += line_total
                currency = sku_snapshot.currency
                checkout_items.append(
                    CheckoutItemSnapshot(
                        sku_id=item.sku_id,
                        quantity=item.quantity,
                        unit_price_amount=sku_snapshot.price_amount,
                        currency=sku_snapshot.currency,
                    )
                )

            now = datetime.now(UTC)
            expires_at = now + timedelta(minutes=CHECKOUT_TTL_MINUTES)

            snapshot = CheckoutSnapshot(
                id=uuid.uuid4(),
                cart_id=cart.id,
                items=tuple(checkout_items),
                pickup_point_id=command.pickup_point_id,
                total_amount=total_amount,
                currency=currency,
                created_at=now,
                expires_at=expires_at,
            )

            await self._cart_repo.save_checkout_snapshot(snapshot)

            attempt_id = uuid.uuid4()
            await self._cart_repo.create_checkout_attempt(
                attempt_id=attempt_id,
                cart_id=cart.id,
                snapshot_id=snapshot.id,
            )

            cart.freeze_for_checkout(snapshot, expires_at)
            await self._cart_repo.update(cart)
            self._uow.register_aggregate(cart)
            await self._uow.commit()

        return InitiateCheckoutResult(
            snapshot_id=snapshot.id,
            attempt_id=attempt_id,
            expires_at=expires_at,
            total_amount=total_amount,
            currency=currency,
        )
