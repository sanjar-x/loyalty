"""
Query handler: get cart with grouped items and live prices.

Direct ORM access is allowed on the read side (CQRS). Prices are
fetched from the SKU read service to ensure freshness.
"""

import uuid
from dataclasses import dataclass

from src.modules.cart.application.constants import (
    DEFAULT_CURRENCY,
    UNKNOWN_PRODUCT_NAME,
)
from src.modules.cart.application.queries.read_models import (
    CartGroupReadModel,
    CartItemReadModel,
    CartReadModel,
)
from src.modules.cart.domain.exceptions import CartNotFoundError
from src.modules.cart.domain.interfaces import ICartRepository, ISkuReadService


@dataclass(frozen=True)
class GetCartQuery:
    identity_id: uuid.UUID | None = None
    anonymous_token: str | None = None


class GetCartHandler:
    """Get a fully-populated cart read model with live prices."""

    def __init__(
        self,
        cart_repo: ICartRepository,
        sku_service: ISkuReadService,
    ) -> None:
        self._cart_repo = cart_repo
        self._sku_service = sku_service

    async def handle(self, query: GetCartQuery) -> CartReadModel:
        cart = None
        if query.identity_id is not None:
            cart = await self._cart_repo.get_active_by_identity(query.identity_id)
        elif query.anonymous_token is not None:
            cart = await self._cart_repo.get_active_by_anonymous(query.anonymous_token)

        if cart is None:
            raise CartNotFoundError()

        # Self-heal: if frozen and expired, unfreeze
        if cart.is_freeze_expired():
            cart.unfreeze("expired")
            await self._cart_repo.update(cart)

        if not cart.items:
            return CartReadModel(
                cart_id=cart.id,
                status=cart.status.value,
            )

        # Batch-load SKU snapshots for live prices
        sku_ids = [item.sku_id for item in cart.items]
        snapshots = await self._sku_service.get_sku_snapshots_batch(sku_ids)

        # Build grouped read model
        groups_map: dict[str, list[CartItemReadModel]] = {}
        total_amount = 0
        currency = DEFAULT_CURRENCY

        for item in cart.items:
            sku_snapshot = snapshots.get(item.sku_id)
            if sku_snapshot is not None:
                line_total = sku_snapshot.price_amount * item.quantity
                total_amount += line_total
                currency = sku_snapshot.currency
                read_item = CartItemReadModel(
                    item_id=item.id,
                    sku_id=item.sku_id,
                    product_id=item.product_id,
                    variant_id=item.variant_id,
                    product_name=sku_snapshot.product_name,
                    variant_label=sku_snapshot.variant_label,
                    image_url=sku_snapshot.image_url,
                    unit_price_amount=sku_snapshot.price_amount,
                    currency=sku_snapshot.currency,
                    quantity=item.quantity,
                    line_total_amount=line_total,
                    supplier_type=item.supplier_type,
                    is_available=sku_snapshot.is_active,
                    added_at=item.added_at,
                )
            else:
                read_item = CartItemReadModel(
                    item_id=item.id,
                    sku_id=item.sku_id,
                    product_id=item.product_id,
                    variant_id=item.variant_id,
                    product_name=UNKNOWN_PRODUCT_NAME,
                    variant_label=None,
                    image_url=None,
                    unit_price_amount=0,
                    currency=DEFAULT_CURRENCY,
                    quantity=item.quantity,
                    line_total_amount=0,
                    supplier_type=item.supplier_type,
                    is_available=False,
                    added_at=item.added_at,
                )

            groups_map.setdefault(item.supplier_type, []).append(read_item)

        groups = [
            CartGroupReadModel(
                supplier_type=st,
                items=items,
                group_total_amount=sum(i.line_total_amount for i in items),
                currency=currency,
            )
            for st, items in groups_map.items()
        ]

        return CartReadModel(
            cart_id=cart.id,
            status=cart.status.value,
            groups=groups,
            total_amount=total_amount,
            currency=currency,
            item_count=len(cart.items),
            created_at=cart.created_at,
            updated_at=cart.updated_at,
        )
