"""Admin order endpoints (manager dashboard).

Routes (under ``/admin/orders``):
* ``GET    /``                       — list orders with status/cursor filters.
* ``GET    /{order_id}``             — admin order detail (raw FSM).
* ``GET    /{order_id}/history``     — order state history (audit log).
* ``POST   /{order_id}/procure``     — manager attaches Chinese tracking number,
                                       Order moves PAID → PROCURED.
* ``POST   /{order_id}/hold``        — put order ON_HOLD.
* ``POST   /{order_id}/resume``      — resume from ON_HOLD.
* ``POST   /{order_id}/force-cancel``— admin-initiated cancel.
* ``PATCH  /{order_id}/pickup-point``— admin override of pickup point.
"""

import uuid
from datetime import datetime

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Depends, Query, status

from src.modules.identity.presentation.dependencies import (
    Auth,
    RequirePermission,
)
from src.modules.order.application.commands.cancel_order import (
    CancelOrderCommand,
    CancelOrderHandler,
)
from src.modules.order.application.commands.change_pickup_point import (
    ChangePickupPointCommand,
    ChangePickupPointHandler,
)
from src.modules.order.application.commands.hold_order import (
    HoldOrderCommand,
    HoldOrderHandler,
)
from src.modules.order.application.commands.procure_order import (
    ProcureOrderCommand,
    ProcureOrderHandler,
)
from src.modules.order.application.commands.resume_order import (
    ResumeOrderCommand,
    ResumeOrderHandler,
)
from src.modules.order.application.queries.admin_list_orders import (
    AdminGetOrderHandler,
    AdminGetOrderQuery,
    AdminListOrdersHandler,
    AdminListOrdersQuery,
)
from src.modules.order.application.queries.get_order_state_history import (
    GetOrderStateHistoryHandler,
    GetOrderStateHistoryQuery,
)
from src.modules.order.application.queries.read_models import AdminOrderReadModel
from src.modules.order.domain.value_objects import (
    CancellationReason,
    HoldReason,
    OrderStatus,
)
from src.modules.order.presentation.schemas import (
    AdminOrderListResponse,
    AdminOrderSchema,
    CancelOrderRequest,
    ChangePickupPointRequest,
    HoldOrderRequest,
    OrderItemSchema,
    OrderStateHistoryEntrySchema,
    ProcureOrderRequest,
)

admin_order_router = APIRouter(
    prefix="/admin/orders",
    tags=["Admin / Orders"],
    route_class=DishkaRoute,
)


def _serialize_admin(model: AdminOrderReadModel) -> AdminOrderSchema:
    return AdminOrderSchema(
        order_id=model.order_id,
        order_number=model.order_number,
        identity_id=model.identity_id,
        cart_id=model.cart_id,
        status=model.status,
        customer_facing_status=model.customer_facing_status,
        total_amount=model.total_amount,
        currency=model.currency,
        cny_rate_at_checkout=model.cny_rate_at_checkout,
        pickup_carrier=model.pickup_carrier,
        pickup_point_id=model.pickup_point_id,
        payment_intent_id=model.payment_intent_id,
        incoming_declaration=model.incoming_declaration,
        procured_by_admin_id=model.procured_by_admin_id,
        procured_at=model.procured_at,
        cross_border_shipment_id=model.cross_border_shipment_id,
        last_mile_shipment_id=model.last_mile_shipment_id,
        pre_hold_status=model.pre_hold_status,
        hold_reason=model.hold_reason,
        hold_started_at=model.hold_started_at,
        hold_until=model.hold_until,
        cancellation_reason=model.cancellation_reason,
        created_at=model.created_at,
        updated_at=model.updated_at,
        items=[
            OrderItemSchema(
                item_id=it.item_id,
                sku_id=it.sku_id,
                product_id=it.product_id,
                variant_id=it.variant_id,
                product_name=it.product_name,
                variant_label=it.variant_label,
                supplier_type=it.supplier_type,
                quantity=it.quantity,
                unit_price_amount=it.unit_price_amount,
                currency=it.currency,
                line_total_amount=it.line_total_amount,
                cross_border_shipment_id=it.cross_border_shipment_id,
                last_mile_shipment_id=it.last_mile_shipment_id,
            )
            for it in model.items
        ],
    )


@admin_order_router.get(
    "",
    response_model=AdminOrderListResponse,
    dependencies=[Depends(RequirePermission("orders:read"))],
)
async def admin_list_orders(
    handler: FromDishka[AdminListOrdersHandler],
    statuses: list[str] | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    cursor: datetime | None = Query(default=None),
) -> AdminOrderListResponse:
    parsed: list[OrderStatus] | None = None
    if statuses:
        parsed = []
        for raw in statuses:
            try:
                parsed.append(OrderStatus(raw))
            except ValueError:
                continue
    page = await handler.handle(
        AdminListOrdersQuery(statuses=parsed, limit=limit, cursor=cursor)
    )
    return AdminOrderListResponse(
        items=[_serialize_admin(o) for o in page.items],
        next_cursor=page.next_cursor,
    )


@admin_order_router.get(
    "/{order_id}",
    response_model=AdminOrderSchema,
    dependencies=[Depends(RequirePermission("orders:read"))],
)
async def admin_get_order(
    order_id: uuid.UUID,
    handler: FromDishka[AdminGetOrderHandler],
) -> AdminOrderSchema:
    rm = await handler.handle(AdminGetOrderQuery(order_id=order_id))
    return _serialize_admin(rm)


@admin_order_router.get(
    "/{order_id}/history",
    response_model=list[OrderStateHistoryEntrySchema],
    dependencies=[Depends(RequirePermission("orders:read"))],
)
async def admin_get_history(
    order_id: uuid.UUID,
    handler: FromDishka[GetOrderStateHistoryHandler],
) -> list[OrderStateHistoryEntrySchema]:
    entries = await handler.handle(GetOrderStateHistoryQuery(order_id=order_id))
    return [
        OrderStateHistoryEntrySchema(
            id=e.id,
            from_status=e.from_status,
            to_status=e.to_status,
            event_type=e.event_type,
            event_id=e.event_id,
            actor_type=e.actor_type,
            actor_id=e.actor_id,
            metadata=e.metadata,
            occurred_at=e.occurred_at,
        )
        for e in entries
    ]


@admin_order_router.post(
    "/{order_id}/procure",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(RequirePermission("orders:procure"))],
)
async def admin_procure_order(
    order_id: uuid.UUID,
    body: ProcureOrderRequest,
    auth: Auth,
    handler: FromDishka[ProcureOrderHandler],
) -> None:
    await handler.handle(
        ProcureOrderCommand(
            order_id=order_id,
            incoming_declaration=body.incoming_declaration,
            admin_id=auth.identity_id,
        )
    )


@admin_order_router.post(
    "/{order_id}/hold",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(RequirePermission("orders:hold_manage"))],
)
async def admin_hold_order(
    order_id: uuid.UUID,
    body: HoldOrderRequest,
    handler: FromDishka[HoldOrderHandler],
) -> None:
    await handler.handle(
        HoldOrderCommand(order_id=order_id, reason=HoldReason(body.reason))
    )


@admin_order_router.post(
    "/{order_id}/resume",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(RequirePermission("orders:hold_manage"))],
)
async def admin_resume_order(
    order_id: uuid.UUID,
    handler: FromDishka[ResumeOrderHandler],
) -> None:
    await handler.handle(ResumeOrderCommand(order_id=order_id))


@admin_order_router.post(
    "/{order_id}/force-cancel",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(RequirePermission("orders:cancel"))],
)
async def admin_force_cancel(
    order_id: uuid.UUID,
    body: CancelOrderRequest,
    auth: Auth,
    handler: FromDishka[CancelOrderHandler],
) -> None:
    try:
        reason = CancellationReason(body.reason)
    except ValueError:
        reason = CancellationReason.MERCHANT_FORCE_CANCEL
    await handler.handle(
        CancelOrderCommand(
            order_id=order_id,
            identity_id=None,
            reason=reason,
            actor_id=str(auth.identity_id),
            idempotency_key=body.idempotency_key,
        )
    )


@admin_order_router.patch(
    "/{order_id}/pickup-point",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(RequirePermission("orders:read"))],
)
async def admin_change_pickup_point(
    order_id: uuid.UUID,
    body: ChangePickupPointRequest,
    handler: FromDishka[ChangePickupPointHandler],
) -> None:
    await handler.handle(
        ChangePickupPointCommand(
            order_id=order_id,
            identity_id=None,
            carrier=body.carrier,
            point_id=body.point_id,
        )
    )
