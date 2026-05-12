"""Anti-corruption adapter: read a confirmed checkout snapshot from cart.

Translates cart's ``CheckoutSnapshotModel`` JSONB payload into Order's
own ``CartCheckoutSnapshot``. The pickup point and CNY rate are pulled
from the snapshot; cart's existing ``pickup_point_id`` is interpreted
as a CDEK point id by default — until cart's snapshot schema carries
``pickup_carrier`` explicitly, the adapter falls back to ``CDEK``. This
keeps Order independent of cart's domain entities.

Whitelisted in tests/architecture as ``("order","cart")``.
"""

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.cart.infrastructure.models import (
    CartItemModel,
    CartModel,
    CheckoutSnapshotModel,
)
from src.modules.order.domain.interfaces import (
    CartCheckoutItemSnapshot,
    CartCheckoutSnapshot,
    ICartSnapshotReader,
)
from src.modules.order.domain.value_objects import (
    PickupCarrier,
    PickupPointPreference,
)
from shared.domain.supplier_type import SupplierType


class CartSnapshotReader(ICartSnapshotReader):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(
        self, *, cart_id: uuid.UUID, snapshot_id: uuid.UUID
    ) -> CartCheckoutSnapshot | None:
        snap_stmt = select(CheckoutSnapshotModel).where(
            CheckoutSnapshotModel.id == snapshot_id,
            CheckoutSnapshotModel.cart_id == cart_id,
        )
        snap = (await self._session.execute(snap_stmt)).scalar_one_or_none()
        if snap is None:
            return None

        cart_stmt = select(CartModel).where(CartModel.id == cart_id)
        cart = (await self._session.execute(cart_stmt)).scalar_one_or_none()
        if cart is None:
            return None

        items_stmt = select(CartItemModel).where(CartItemModel.cart_id == cart_id)
        cart_items = list((await self._session.execute(items_stmt)).scalars().all())
        item_by_sku = {it.sku_id: it for it in cart_items}

        items_payload: list[dict[str, Any]] = list(snap.items_json or [])
        items: list[CartCheckoutItemSnapshot] = []
        for entry in items_payload:
            sku_id = uuid.UUID(str(entry["sku_id"]))
            qty = int(entry["quantity"])
            unit_price = int(entry["unit_price_amount"])
            currency = str(entry["currency"])
            cart_item = item_by_sku.get(sku_id)
            items.append(
                CartCheckoutItemSnapshot(
                    sku_id=sku_id,
                    product_id=cart_item.product_id if cart_item else sku_id,
                    variant_id=cart_item.variant_id if cart_item else sku_id,
                    product_name="",
                    variant_label=None,
                    supplier_type=SupplierType(cart_item.supplier_type)
                    if cart_item
                    else SupplierType.LOCAL,
                    quantity=qty,
                    unit_price_amount=unit_price,
                    currency=currency,
                )
            )

        # Cart's snapshot today carries only ``pickup_point_id`` (no carrier
        # discrimination); default to CDEK and let the admin endpoint patch
        try:
            carrier = PickupCarrier(snap.pickup_carrier)
        except ValueError:
            carrier = PickupCarrier.CDEK
        pickup = PickupPointPreference(
            carrier=carrier,
            point_id=str(snap.pickup_point_id),
        )

        return CartCheckoutSnapshot(
            cart_id=snap.cart_id,
            snapshot_id=snap.id,
            pickup_point=pickup,
            recipient_id=snap.recipient_id,
            total_amount=snap.total_amount,
            currency=snap.currency,
            cny_rate_at_checkout=None,
            items=tuple(items),
        )
