"""
Cart repository — Data Mapper implementation.

Translates between Cart domain entities and CartModel/CartItemModel ORM models.
"""

import uuid
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.cart.domain.entities import Cart, CartItem
from src.modules.cart.domain.interfaces import ICartRepository
from src.modules.cart.domain.value_objects import (
    CartStatus,
    CheckoutItemSnapshot,
    CheckoutSnapshot,
)
from src.modules.cart.infrastructure.models import (
    CartItemModel,
    CartModel,
    CheckoutAttemptModel,
    CheckoutSnapshotModel,
)


class CartRepository(ICartRepository):
    """SQLAlchemy-based cart repository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # Domain ↔ ORM mapping
    # ------------------------------------------------------------------

    @staticmethod
    def _to_domain(model: CartModel) -> Cart:
        items = [
            CartItem(
                id=item_model.id,
                sku_id=item_model.sku_id,
                product_id=item_model.product_id,
                variant_id=item_model.variant_id,
                supplier_type=item_model.supplier_type,
                quantity=item_model.quantity,
                added_at=item_model.added_at,
            )
            for item_model in model.items
        ]
        cart = Cart(
            id=model.id,
            identity_id=model.identity_id,
            anonymous_token=model.anonymous_token,
            status=CartStatus(model.status),
            version=model.version,
            frozen_until=model.frozen_until,
            created_at=model.created_at,
            updated_at=model.updated_at,
            last_repriced_at=model.last_repriced_at,
            items=items,
        )
        cart.clear_domain_events()
        return cart

    @staticmethod
    def _to_orm(cart: Cart, model: CartModel | None = None) -> CartModel:
        if model is None:
            model = CartModel(id=cart.id)

        model.identity_id = cart.identity_id
        model.anonymous_token = cart.anonymous_token
        model.status = cart.status.value
        model.version = cart.version
        model.frozen_until = cart.frozen_until
        model.created_at = cart.created_at
        model.updated_at = cart.updated_at
        model.last_repriced_at = cart.last_repriced_at

        # Sync items
        existing_items = {item.id: item for item in model.items}
        domain_ids = {item.id for item in cart.items}

        # Remove deleted items
        model.items = [item for item in model.items if item.id in domain_ids]

        # Add/update items
        for domain_item in cart.items:
            if domain_item.id in existing_items:
                orm_item = existing_items[domain_item.id]
                orm_item.quantity = domain_item.quantity
            else:
                model.items.append(
                    CartItemModel(
                        id=domain_item.id,
                        cart_id=cart.id,
                        sku_id=domain_item.sku_id,
                        product_id=domain_item.product_id,
                        variant_id=domain_item.variant_id,
                        supplier_type=domain_item.supplier_type,
                        quantity=domain_item.quantity,
                        added_at=domain_item.added_at,
                    )
                )

        return model

    # ------------------------------------------------------------------
    # Repository methods
    # ------------------------------------------------------------------

    async def add(self, cart: Cart) -> Cart:
        model = self._to_orm(cart)
        self._session.add(model)
        await self._session.flush()
        return cart

    async def get(self, cart_id: uuid.UUID) -> Cart | None:
        stmt = select(CartModel).where(CartModel.id == cart_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def get_for_update(self, cart_id: uuid.UUID) -> Cart | None:
        stmt = select(CartModel).where(CartModel.id == cart_id).with_for_update()
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def get_active_by_identity(self, identity_id: uuid.UUID) -> Cart | None:
        stmt = select(CartModel).where(
            CartModel.identity_id == identity_id,
            CartModel.status == "active",
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def get_active_or_frozen_by_identity(self, identity_id: uuid.UUID) -> Cart | None:
        stmt = select(CartModel).where(
            CartModel.identity_id == identity_id,
            CartModel.status.in_(["active", "frozen"]),
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def get_active_by_anonymous(self, anonymous_token: str) -> Cart | None:
        stmt = select(CartModel).where(
            CartModel.anonymous_token == anonymous_token,
            CartModel.status == "active",
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def update(self, cart: Cart) -> Cart:
        stmt = select(CartModel).where(CartModel.id == cart.id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            msg = f"Cart {cart.id} not found in DB"
            raise ValueError(msg)
        self._to_orm(cart, model)
        await self._session.flush()
        return cart

    # ------------------------------------------------------------------
    # Checkout snapshot & attempt methods
    # ------------------------------------------------------------------

    async def save_checkout_snapshot(self, snapshot: CheckoutSnapshot) -> None:
        model = CheckoutSnapshotModel(
            id=snapshot.id,
            cart_id=snapshot.cart_id,
            items_json=[
                {
                    "sku_id": str(item.sku_id),
                    "quantity": item.quantity,
                    "unit_price_amount": item.unit_price_amount,
                    "currency": item.currency,
                }
                for item in snapshot.items
            ],
            pickup_point_id=snapshot.pickup_point_id,
            total_amount=snapshot.total_amount,
            currency=snapshot.currency,
            created_at=snapshot.created_at,
            expires_at=snapshot.expires_at,
        )
        self._session.add(model)
        await self._session.flush()

    async def get_checkout_snapshot(
        self, snapshot_id: uuid.UUID
    ) -> CheckoutSnapshot | None:
        stmt = select(CheckoutSnapshotModel).where(
            CheckoutSnapshotModel.id == snapshot_id
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return None

        items = tuple(
            CheckoutItemSnapshot(
                sku_id=uuid.UUID(item["sku_id"]),
                quantity=item["quantity"],
                unit_price_amount=item["unit_price_amount"],
                currency=item["currency"],
            )
            for item in model.items_json
        )

        return CheckoutSnapshot(
            id=model.id,
            cart_id=model.cart_id,
            items=items,
            pickup_point_id=model.pickup_point_id,
            total_amount=model.total_amount,
            currency=model.currency,
            created_at=model.created_at,
            expires_at=model.expires_at,
        )

    async def create_checkout_attempt(
        self,
        *,
        attempt_id: uuid.UUID,
        cart_id: uuid.UUID,
        snapshot_id: uuid.UUID,
    ) -> None:
        model = CheckoutAttemptModel(
            id=attempt_id,
            cart_id=cart_id,
            snapshot_id=snapshot_id,
            status="pending",
        )
        self._session.add(model)
        await self._session.flush()

    async def get_pending_checkout_attempt(self, cart_id: uuid.UUID) -> dict | None:
        stmt = select(CheckoutAttemptModel).where(
            CheckoutAttemptModel.cart_id == cart_id,
            CheckoutAttemptModel.status == "pending",
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return {
            "id": model.id,
            "cart_id": model.cart_id,
            "snapshot_id": model.snapshot_id,
            "status": model.status,
            "created_at": model.created_at,
        }

    async def resolve_checkout_attempt(
        self,
        attempt_id: uuid.UUID,
        *,
        status: str,
        resolved_at: datetime,
    ) -> None:
        stmt = (
            update(CheckoutAttemptModel)
            .where(CheckoutAttemptModel.id == attempt_id)
            .values(status=status, resolved_at=resolved_at)
        )
        await self._session.execute(stmt)
        await self._session.flush()
