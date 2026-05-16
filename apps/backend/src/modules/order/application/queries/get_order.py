"""Query: customer-facing single order detail (укрупнённый status)."""

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.modules.order.application.queries.read_models import (
    CustomerOrderReadModel,
    OrderItemReadModel,
)
from src.modules.order.domain.exceptions import OrderNotFoundError
from src.modules.order.domain.value_objects import (
    OrderNumber,
    OrderStatus,
    to_customer_facing,
)
from src.modules.order.infrastructure.models import OrderItemModel, OrderModel


@dataclass(frozen=True)
class GetOrderQuery:
    order_id: uuid.UUID
    identity_id: uuid.UUID


class GetOrderHandler:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def handle(self, query: GetOrderQuery) -> CustomerOrderReadModel:
        stmt = (
            select(OrderModel)
            .where(OrderModel.id == query.order_id)
            .where(OrderModel.identity_id == query.identity_id)
            .options(selectinload(OrderModel.items))
        )
        row: OrderModel | None = (
            await self._session.execute(stmt)
        ).scalar_one_or_none()
        if row is None:
            raise OrderNotFoundError(order_id=str(query.order_id))
        return _to_customer_read_model(row)


def _to_customer_read_model(row: OrderModel) -> CustomerOrderReadModel:
    raw_status = OrderStatus(row.status)
    return CustomerOrderReadModel(
        order_id=row.id,
        order_number=OrderNumber.from_id(row.id, row.created_at).value,
        status=to_customer_facing(raw_status).value,
        raw_status=raw_status.value,
        total_amount=row.total_amount,
        delivery_amount=row.delivery_amount,
        delivery_quote_id=row.delivery_quote_id,
        currency=row.currency,
        pickup_carrier=row.pickup_carrier,
        pickup_point_id=row.pickup_point_id,
        incoming_declaration=row.incoming_declaration,
        cross_border_tracking=row.cross_border_tracking,
        last_mile_tracking=row.last_mile_tracking,
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
    )
