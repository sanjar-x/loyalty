"""Data Mapper for the Order aggregate — Loyality FSM."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.modules.order.domain.entities import (
    HOLD_TTL_DAYS,
    RETURN_WINDOW_DAYS,
    Order,
    OrderItem,
)
from src.modules.order.domain.interfaces import IOrderRepository
from src.modules.order.domain.recipient_snapshot import RecipientSnapshot
from src.modules.order.domain.value_objects import (
    CancellationReason,
    HoldReason,
    IncomingDeclaration,
    OrderStatus,
    PickupCarrier,
    PickupPointPreference,
)
from src.modules.order.infrastructure.models import OrderItemModel, OrderModel
from src.shared.domain.supplier_type import SupplierType

__all__ = [
    "HOLD_TTL_DAYS",
    "RETURN_WINDOW_DAYS",
    "OrderRepository",
    "close_threshold",
    "stuck_in_cn_threshold",
]


class OrderRepository(IOrderRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, order: Order) -> Order:
        row = OrderModel(
            id=order.id,
            identity_id=order.identity_id,
            cart_id=order.cart_id,
            status=order.status.value,
            total_amount=order.total_amount,
            currency=order.currency,
            cny_rate_at_checkout=order.cny_rate_at_checkout,
            pickup_carrier=order.pickup_point.carrier.value,
            pickup_point_id=order.pickup_point.point_id,
            recipient_id=uuid.UUID(order.recipient_snapshot.recipient_id),
            recipient_full_name_ru=order.recipient_snapshot.full_name_ru,
            recipient_full_name_lat=order.recipient_snapshot.full_name_lat,
            recipient_phone=order.recipient_snapshot.phone,
            recipient_email=order.recipient_snapshot.email,
            recipient_passport_serial=order.recipient_snapshot.passport_serial,
            recipient_passport_number=order.recipient_snapshot.passport_number,
            recipient_passport_issue_date=order.recipient_snapshot.passport_issue_date,
            recipient_birth_date=order.recipient_snapshot.birth_date,
            recipient_inn=order.recipient_snapshot.inn,
            payment_intent_id=order.payment_intent_id,
            incoming_declaration=(
                order.incoming_declaration.value if order.incoming_declaration else None
            ),
            procured_by_admin_id=order.procured_by_admin_id,
            procured_at=order.procured_at,
            cross_border_shipment_id=order.cross_border_shipment_id,
            last_mile_shipment_id=order.last_mile_shipment_id,
            cross_border_tracking=None,
            last_mile_tracking=None,
            pre_hold_status=(
                order.pre_hold_status.value if order.pre_hold_status else None
            ),
            hold_reason=order.hold_reason.value if order.hold_reason else None,
            hold_started_at=order.hold_started_at,
            hold_until=order.hold_until,
            cancellation_reason=(
                order.cancellation_reason.value if order.cancellation_reason else None
            ),
            version=order.version,
            created_at=order.created_at,
            updated_at=order.updated_at,
        )
        for itm in order.items:
            row.items.append(_item_to_orm(itm, order.id))
        self._session.add(row)
        await self._session.flush()
        return order

    async def get(self, order_id: uuid.UUID) -> Order | None:
        return await self._fetch_one(OrderModel.id == order_id)

    async def get_for_update(self, order_id: uuid.UUID) -> Order | None:
        return await self._fetch_one(OrderModel.id == order_id, lock=True)

    async def get_by_payment_intent(self, payment_intent_id: uuid.UUID) -> Order | None:
        return await self._fetch_one(OrderModel.payment_intent_id == payment_intent_id)

    async def get_by_incoming_declaration(self, declaration: str) -> Order | None:
        return await self._fetch_one(OrderModel.incoming_declaration == declaration)

    async def get_by_cross_border_shipment(
        self, shipment_id: uuid.UUID
    ) -> Order | None:
        return await self._fetch_one(OrderModel.cross_border_shipment_id == shipment_id)

    async def get_by_last_mile_shipment(self, shipment_id: uuid.UUID) -> Order | None:
        return await self._fetch_one(OrderModel.last_mile_shipment_id == shipment_id)

    async def update(self, order: Order) -> Order:
        stmt = (
            select(OrderModel)
            .where(OrderModel.id == order.id)
            .options(selectinload(OrderModel.items))
        )
        row = (await self._session.execute(stmt)).scalar_one()
        row.status = order.status.value
        row.total_amount = order.total_amount
        row.currency = order.currency
        row.cny_rate_at_checkout = order.cny_rate_at_checkout
        row.pickup_carrier = order.pickup_point.carrier.value
        row.pickup_point_id = order.pickup_point.point_id
        # Recipient snapshot is immutable in normal flow but can be refreshed
        # via Order.refresh_recipient_snapshot() — persist changes if any.
        row.recipient_id = uuid.UUID(order.recipient_snapshot.recipient_id)
        row.recipient_full_name_ru = order.recipient_snapshot.full_name_ru
        row.recipient_full_name_lat = order.recipient_snapshot.full_name_lat
        row.recipient_phone = order.recipient_snapshot.phone
        row.recipient_email = order.recipient_snapshot.email
        row.recipient_passport_serial = order.recipient_snapshot.passport_serial
        row.recipient_passport_number = order.recipient_snapshot.passport_number
        row.recipient_passport_issue_date = order.recipient_snapshot.passport_issue_date
        row.recipient_birth_date = order.recipient_snapshot.birth_date
        row.recipient_inn = order.recipient_snapshot.inn
        row.payment_intent_id = order.payment_intent_id
        row.incoming_declaration = (
            order.incoming_declaration.value if order.incoming_declaration else None
        )
        row.procured_by_admin_id = order.procured_by_admin_id
        row.procured_at = order.procured_at
        row.cross_border_shipment_id = order.cross_border_shipment_id
        row.last_mile_shipment_id = order.last_mile_shipment_id
        row.pre_hold_status = (
            order.pre_hold_status.value if order.pre_hold_status else None
        )
        row.hold_reason = order.hold_reason.value if order.hold_reason else None
        row.hold_started_at = order.hold_started_at
        row.hold_until = order.hold_until
        row.cancellation_reason = (
            order.cancellation_reason.value if order.cancellation_reason else None
        )
        row.version = order.version + 1
        row.updated_at = order.updated_at

        existing_by_id = {it.id: it for it in row.items}
        seen: set[uuid.UUID] = set()
        for itm in order.items:
            seen.add(itm.id)
            existing = existing_by_id.get(itm.id)
            if existing is None:
                row.items.append(_item_to_orm(itm, order.id))
            else:
                existing.cross_border_shipment_id = itm.cross_border_shipment_id
                existing.last_mile_shipment_id = itm.last_mile_shipment_id
                existing.quantity = itm.quantity
        for orphan_id, orphan in list(existing_by_id.items()):
            if orphan_id not in seen:
                row.items.remove(orphan)

        await self._session.flush()
        return order

    async def list_by_identity(
        self,
        identity_id: uuid.UUID,
        *,
        limit: int,
        cursor: datetime | None,
    ) -> list[Order]:
        stmt = (
            select(OrderModel)
            .where(OrderModel.identity_id == identity_id)
            .options(selectinload(OrderModel.items))
            .order_by(OrderModel.created_at.desc(), OrderModel.id.desc())
            .limit(limit)
        )
        if cursor is not None:
            stmt = stmt.where(OrderModel.created_at < cursor)
        rows = (await self._session.execute(stmt)).scalars().all()
        return [_to_domain(r) for r in rows]

    async def list_for_admin(
        self,
        *,
        statuses: list[OrderStatus] | None,
        limit: int,
        cursor: datetime | None,
    ) -> list[Order]:
        stmt = (
            select(OrderModel)
            .options(selectinload(OrderModel.items))
            .order_by(OrderModel.created_at.desc(), OrderModel.id.desc())
            .limit(limit)
        )
        if statuses:
            stmt = stmt.where(OrderModel.status.in_([s.value for s in statuses]))
        if cursor is not None:
            stmt = stmt.where(OrderModel.created_at < cursor)
        rows = (await self._session.execute(stmt)).scalars().all()
        return [_to_domain(r) for r in rows]

    async def find_stuck_in_cn(self, *, threshold: datetime) -> list[Order]:
        stmt = (
            select(OrderModel)
            .where(OrderModel.status == OrderStatus.PROCURED.value)
            .where(OrderModel.updated_at < threshold)
            .options(selectinload(OrderModel.items))
            .limit(100)
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return [_to_domain(r) for r in rows]

    async def find_hold_ttl_expired(self) -> list[Order]:
        now = datetime.now(UTC)
        stmt = (
            select(OrderModel)
            .where(OrderModel.status == OrderStatus.ON_HOLD.value)
            .where(OrderModel.hold_until.isnot(None))
            .where(OrderModel.hold_until < now)
            .options(selectinload(OrderModel.items))
            .limit(100)
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return [_to_domain(r) for r in rows]

    async def find_eligible_for_close(self, *, threshold: datetime) -> list[Order]:
        stmt = (
            select(OrderModel)
            .where(OrderModel.status == OrderStatus.DELIVERED.value)
            .where(OrderModel.updated_at < threshold)
            .options(selectinload(OrderModel.items))
            .limit(100)
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return [_to_domain(r) for r in rows]

    async def _fetch_one(self, predicate, *, lock: bool = False) -> Order | None:
        stmt = (
            select(OrderModel).where(predicate).options(selectinload(OrderModel.items))
        )
        if lock:
            stmt = stmt.with_for_update()
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return _to_domain(row) if row else None


def _item_to_orm(itm: OrderItem, order_id: uuid.UUID) -> OrderItemModel:
    return OrderItemModel(
        id=itm.id,
        order_id=order_id,
        sku_id=itm.sku_id,
        product_id=itm.product_id,
        variant_id=itm.variant_id,
        product_name=itm.product_name,
        variant_label=itm.variant_label,
        supplier_type=itm.supplier_type,
        quantity=itm.quantity,
        unit_price_amount=itm.unit_price_amount,
        currency=itm.currency,
        cross_border_shipment_id=itm.cross_border_shipment_id,
        last_mile_shipment_id=itm.last_mile_shipment_id,
    )


def _to_domain(row: OrderModel) -> Order:
    items = [
        OrderItem(
            id=it.id,
            sku_id=it.sku_id,
            product_id=it.product_id,
            variant_id=it.variant_id,
            product_name=it.product_name,
            variant_label=it.variant_label,
            supplier_type=SupplierType(it.supplier_type),
            quantity=it.quantity,
            unit_price_amount=it.unit_price_amount,
            currency=it.currency,
            cross_border_shipment_id=it.cross_border_shipment_id,
            last_mile_shipment_id=it.last_mile_shipment_id,
        )
        for it in row.items
    ]
    return Order(
        id=row.id,
        identity_id=row.identity_id,
        cart_id=row.cart_id,
        status=OrderStatus(row.status),
        total_amount=row.total_amount,
        currency=row.currency,
        cny_rate_at_checkout=row.cny_rate_at_checkout,
        pickup_point=PickupPointPreference(
            carrier=PickupCarrier(row.pickup_carrier),
            point_id=row.pickup_point_id,
        ),
        recipient_snapshot=RecipientSnapshot(
            recipient_id=str(row.recipient_id),
            full_name_ru=row.recipient_full_name_ru,
            full_name_lat=row.recipient_full_name_lat,
            phone=row.recipient_phone,
            email=row.recipient_email,
            passport_serial=row.recipient_passport_serial,
            passport_number=row.recipient_passport_number,
            passport_issue_date=row.recipient_passport_issue_date,
            birth_date=row.recipient_birth_date,
            inn=row.recipient_inn,
        ),
        payment_intent_id=row.payment_intent_id,
        incoming_declaration=(
            IncomingDeclaration(value=row.incoming_declaration)
            if row.incoming_declaration
            else None
        ),
        procured_by_admin_id=row.procured_by_admin_id,
        procured_at=row.procured_at,
        cross_border_shipment_id=row.cross_border_shipment_id,
        last_mile_shipment_id=row.last_mile_shipment_id,
        pre_hold_status=(
            OrderStatus(row.pre_hold_status) if row.pre_hold_status else None
        ),
        hold_reason=HoldReason(row.hold_reason) if row.hold_reason else None,
        hold_started_at=row.hold_started_at,
        hold_until=row.hold_until,
        cancellation_reason=(
            CancellationReason(row.cancellation_reason)
            if row.cancellation_reason
            else None
        ),
        created_at=row.created_at,
        updated_at=row.updated_at,
        version=row.version,
        items=items,
    )


def stuck_in_cn_threshold(now: datetime, *, days: int = 14) -> datetime:
    return now - timedelta(days=days)


def close_threshold(now: datetime, *, days: int = RETURN_WINDOW_DAYS) -> datetime:
    return now - timedelta(days=days)
