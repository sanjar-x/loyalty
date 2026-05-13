"""Query: customer-facing tracking page for an order.

Joins together three sources:

* ``orders`` row — gives us the order, customer-facing status, and the
  ``incoming_declaration`` (Chinese tracking number).
* ``dobropost_shipment_mappings`` — DobroPost track number + last
  observed status_id (translated to a human label).
* ``order_state_history`` — FSM transitions, used to render the
  timeline (created → paid → procured → ...).

The endpoint is read-only and intentionally lives next to ``get_order``
in ``application.queries`` (CQRS read-side).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.order.application.queries.read_models import (
    OrderTrackingReadModel,
    TrackingStepReadModel,
)
from src.modules.order.domain.exceptions import OrderNotFoundError
from src.modules.order.domain.value_objects import (
    OrderNumber,
    OrderStatus,
    to_customer_facing,
)
from src.modules.order.infrastructure.dobropost_status_map import status_label
from src.modules.order.infrastructure.models import (
    DobroPostShipmentMappingModel,
    OrderModel,
    OrderStateHistoryModel,
)


@dataclass(frozen=True)
class GetOrderTrackingQuery:
    order_id: uuid.UUID
    identity_id: uuid.UUID


_FSM_LABELS: dict[str, str] = {
    "pending": "Заказ создан",
    "paid": "Оплата подтверждена",
    "procured": "Менеджер выкупил товар",
    "on_hold": "Заказ на удержании",
    "arrived_in_ru": "Прибыл в Россию",
    "in_last_mile": "В пути по России",
    "awaiting_pickup": "Готов к выдаче в пункте",
    "delivered": "Получен покупателем",
    "returning_to_ru_warehouse": "Возврат на склад",
    "not_delivered": "Не доставлен",
    "return_in_progress": "Возврат оформляется",
    "returned": "Возврат завершён",
    "closed": "Заказ закрыт",
    "cancelled": "Заказ отменён",
}


def _fsm_label(status: str) -> str:
    return _FSM_LABELS.get(status, status)


def _leg_for(status: str) -> str:
    if status in {"pending", "paid", "procured", "cancelled", "on_hold"}:
        return "order"
    if status in {"arrived_in_ru"}:
        return "cross_border"
    return "last_mile"


class GetOrderTrackingHandler:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def handle(self, query: GetOrderTrackingQuery) -> OrderTrackingReadModel:
        order_stmt = (
            select(OrderModel)
            .where(OrderModel.id == query.order_id)
            .where(OrderModel.identity_id == query.identity_id)
        )
        order = (await self._session.execute(order_stmt)).scalar_one_or_none()
        if order is None:
            raise OrderNotFoundError(order_id=str(query.order_id))

        mapping_stmt = select(DobroPostShipmentMappingModel).where(
            DobroPostShipmentMappingModel.order_id == query.order_id
        )
        mapping = (await self._session.execute(mapping_stmt)).scalar_one_or_none()

        history_stmt = (
            select(OrderStateHistoryModel)
            .where(OrderStateHistoryModel.order_id == query.order_id)
            .order_by(OrderStateHistoryModel.occurred_at.asc())
        )
        history = (await self._session.execute(history_stmt)).scalars().all()

        steps: list[TrackingStepReadModel] = [
            TrackingStepReadModel(
                occurred_at=h.occurred_at,
                code=f"order:{h.to_status}",
                label=_fsm_label(h.to_status),
                leg=_leg_for(h.to_status),
            )
            for h in history
        ]
        if mapping is not None and mapping.last_status_id is not None:
            steps.append(
                TrackingStepReadModel(
                    occurred_at=mapping.last_status_at or mapping.updated_at,
                    code=f"dp:{mapping.last_status_id}",
                    label=status_label(mapping.last_status_id),
                    leg="cross_border",
                )
            )
        steps.sort(key=lambda s: s.occurred_at)

        raw_status = OrderStatus(order.status)
        return OrderTrackingReadModel(
            order_id=order.id,
            order_number=OrderNumber.from_id(order.id, order.created_at).value,
            status=to_customer_facing(raw_status).value,
            raw_status=raw_status.value,
            incoming_declaration=order.incoming_declaration,
            cross_border_track=(mapping.dp_track_number if mapping else None)
            or order.cross_border_tracking,
            last_mile_track=order.last_mile_tracking,
            cross_border_status_id=(mapping.last_status_id if mapping else None),
            cross_border_status_label=(
                status_label(mapping.last_status_id)
                if mapping and mapping.last_status_id is not None
                else None
            ),
            steps=steps,
        )
