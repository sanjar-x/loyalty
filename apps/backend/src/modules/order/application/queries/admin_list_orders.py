"""Admin query: list orders with raw status filters."""

import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.modules.order.application.queries.read_models import (
    AdminOrderListPage,
    AdminOrderReadModel,
    OrderItemReadModel,
    RecipientSnapshotReadModel,
)
from src.modules.order.domain.exceptions import OrderNotFoundError
from src.modules.order.domain.value_objects import (
    OrderNumber,
    OrderStatus,
    to_customer_facing,
)
from src.modules.order.infrastructure.models import OrderItemModel, OrderModel


def _to_recipient_snapshot(row: OrderModel) -> RecipientSnapshotReadModel:
    """Read-projection of the order's frozen customs recipient snapshot.

    Mirrors the columns persisted by ``CreateOrderFromCartHandler`` —
    pure column-to-field mapping, no joins. Admin-only — never returned
    via customer-facing read models.
    """
    return RecipientSnapshotReadModel(
        recipient_id=row.recipient_id,
        full_name_ru=row.recipient_full_name_ru,
        full_name_lat=row.recipient_full_name_lat,
        phone=row.recipient_phone,
        email=row.recipient_email,
        passport_serial=row.recipient_passport_serial,
        passport_number=row.recipient_passport_number,
        passport_issue_date=row.recipient_passport_issue_date,
        birth_date=row.recipient_birth_date,
        inn=row.recipient_inn,
    )


def _to_admin_read_model(row: OrderModel) -> AdminOrderReadModel:
    raw_status = OrderStatus(row.status)
    return AdminOrderReadModel(
        order_id=row.id,
        order_number=OrderNumber.from_id(row.id, row.created_at).value,
        identity_id=row.identity_id,
        cart_id=row.cart_id,
        status=raw_status.value,
        customer_facing_status=to_customer_facing(raw_status).value,
        total_amount=row.total_amount,
        delivery_amount=row.delivery_amount,
        delivery_quote_id=row.delivery_quote_id,
        currency=row.currency,
        cny_rate_at_checkout=(
            str(row.cny_rate_at_checkout)
            if row.cny_rate_at_checkout is not None
            else None
        ),
        pickup_carrier=row.pickup_carrier,
        pickup_point_id=row.pickup_point_id,
        payment_intent_id=row.payment_intent_id,
        incoming_declaration=row.incoming_declaration,
        procured_by_admin_id=row.procured_by_admin_id,
        procured_at=row.procured_at,
        cross_border_shipment_id=row.cross_border_shipment_id,
        last_mile_shipment_id=row.last_mile_shipment_id,
        pre_hold_status=row.pre_hold_status,
        hold_reason=row.hold_reason,
        hold_started_at=row.hold_started_at,
        hold_until=row.hold_until,
        cancellation_reason=row.cancellation_reason,
        created_at=row.created_at,
        updated_at=row.updated_at,
        items=[
            OrderItemReadModel(
                item_id=it.id,
                sku_id=it.sku_id,
                product_id=it.product_id,
                variant_id=it.variant_id,
                product_name=it.product_name,
                variant_label=it.variant_label,
                supplier_type=it.supplier_type,
                quantity=it.quantity,
                unit_price_amount=it.unit_price_amount,
                currency=it.currency,
                line_total_amount=it.unit_price_amount * it.quantity,
                cross_border_shipment_id=it.cross_border_shipment_id,
                last_mile_shipment_id=it.last_mile_shipment_id,
            )
            for it in sorted(row.items, key=lambda i: i.id)
            if isinstance(it, OrderItemModel)
        ],
        recipient_snapshot=_to_recipient_snapshot(row),
    )


@dataclass(frozen=True)
class AdminGetOrderQuery:
    order_id: uuid.UUID


class AdminGetOrderHandler:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def handle(self, query: AdminGetOrderQuery) -> AdminOrderReadModel:
        stmt = (
            select(OrderModel)
            .where(OrderModel.id == query.order_id)
            .options(selectinload(OrderModel.items))
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        if row is None:
            raise OrderNotFoundError(order_id=str(query.order_id))
        return _to_admin_read_model(row)


@dataclass(frozen=True)
class AdminListOrdersQuery:
    statuses: list[OrderStatus] | None = None
    limit: int = 50
    cursor: datetime | None = None


class AdminListOrdersHandler:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def handle(self, query: AdminListOrdersQuery) -> AdminOrderListPage:
        limit = max(1, min(query.limit, 200))
        stmt = (
            select(OrderModel)
            .options(selectinload(OrderModel.items))
            .order_by(OrderModel.created_at.desc(), OrderModel.id.desc())
            .limit(limit + 1)
        )
        if query.statuses:
            stmt = stmt.where(OrderModel.status.in_([s.value for s in query.statuses]))
        if query.cursor is not None:
            stmt = stmt.where(OrderModel.created_at < query.cursor)
        rows = list((await self._session.execute(stmt)).scalars().all())
        has_more = len(rows) > limit
        rows = rows[:limit]
        items = [_to_admin_read_model(r) for r in rows]
        next_cursor = items[-1].created_at if has_more and items else None
        return AdminOrderListPage(items=items, next_cursor=next_cursor)
