"""Query handler: lightweight cart summary (count + total)."""

import uuid
from dataclasses import dataclass

from src.modules.cart.application.queries.read_models import CartSummaryReadModel
from src.modules.cart.domain.exceptions import CartNotFoundError
from src.modules.cart.domain.interfaces import ICartRepository, ISkuReadService


@dataclass(frozen=True)
class GetCartSummaryQuery:
    identity_id: uuid.UUID | None = None
    anonymous_token: str | None = None


class GetCartSummaryHandler:
    """Get cart item count and total without full grouping."""

    def __init__(
        self,
        cart_repo: ICartRepository,
        sku_service: ISkuReadService,
    ) -> None:
        self._cart_repo = cart_repo
        self._sku_service = sku_service

    async def handle(self, query: GetCartSummaryQuery) -> CartSummaryReadModel:
        cart = None
        if query.identity_id is not None:
            cart = await self._cart_repo.get_active_by_identity(query.identity_id)
        elif query.anonymous_token is not None:
            cart = await self._cart_repo.get_active_by_anonymous(query.anonymous_token)

        if cart is None:
            raise CartNotFoundError()

        if not cart.items:
            return CartSummaryReadModel(
                cart_id=cart.id,
                item_count=0,
                total_amount=0,
            )

        sku_ids = [item.sku_id for item in cart.items]
        snapshots = await self._sku_service.get_sku_snapshots_batch(sku_ids)

        total = 0
        for item in cart.items:
            sku_snapshot = snapshots.get(item.sku_id)
            if sku_snapshot is not None:
                total += sku_snapshot.price_amount * item.quantity

        return CartSummaryReadModel(
            cart_id=cart.id,
            item_count=len(cart.items),
            total_amount=total,
        )
