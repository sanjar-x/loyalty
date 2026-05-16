"""Customer-facing order endpoints.

Routes (under ``/orders``):
* ``POST   /``                — create order from cart snapshot.
* ``GET    /``                — list my orders.
* ``GET    /{order_id}``      — order detail (customer-facing status).
* ``POST   /{order_id}/cancel`` — cancel before procurement.
* ``PATCH  /{order_id}/pickup-point`` — change pickup point before last-mile.
"""

import uuid
from datetime import datetime
from typing import Annotated

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Path, Query, status

from src.modules.identity.presentation.dependencies import Auth
from src.modules.order.application.commands.cancel_order import (
    CancelOrderCommand,
    CancelOrderHandler,
)
from src.modules.order.application.commands.change_pickup_point import (
    ChangePickupPointCommand,
    ChangePickupPointHandler,
)
from src.modules.order.application.commands.create_order_from_cart import (
    CreateOrderFromCartCommand,
    CreateOrderFromCartHandler,
)
from src.modules.order.application.commands.refresh_recipient_snapshot import (
    RefreshRecipientSnapshotCommand,
    RefreshRecipientSnapshotHandler,
)
from src.modules.order.application.queries.get_order import (
    GetOrderHandler,
    GetOrderQuery,
)
from src.modules.order.application.queries.get_order_tracking import (
    GetOrderTrackingHandler,
    GetOrderTrackingQuery,
)
from src.modules.order.application.queries.list_my_orders import (
    ListMyOrdersHandler,
    ListMyOrdersQuery,
)
from src.modules.order.application.queries.read_models import (
    CustomerOrderReadModel,
)
from src.modules.order.domain.value_objects import CancellationReason
from src.modules.order.presentation.schemas import (
    CancelOrderRequest,
    ChangePickupPointRequest,
    CreateOrderRequest,
    CreateOrderResponse,
    CustomerOrderListResponse,
    CustomerOrderSchema,
    OrderItemSchema,
    OrderTrackingResponse,
    TrackingStepSchema,
)

order_router = APIRouter(
    prefix="/orders",
    tags=["Orders"],
    route_class=DishkaRoute,
)


def _serialize(model: CustomerOrderReadModel) -> CustomerOrderSchema:
    return CustomerOrderSchema(
        order_id=model.order_id,
        order_number=model.order_number,
        status=model.status,
        raw_status=model.raw_status,
        total_amount=model.total_amount,
        delivery_amount=model.delivery_amount,
        delivery_quote_id=model.delivery_quote_id,
        currency=model.currency,
        pickup_carrier=model.pickup_carrier,
        pickup_point_id=model.pickup_point_id,
        incoming_declaration=model.incoming_declaration,
        cross_border_tracking=model.cross_border_tracking,
        last_mile_tracking=model.last_mile_tracking,
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


@order_router.post(
    "",
    response_model=CreateOrderResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_order(
    body: CreateOrderRequest,
    auth: Auth,
    handler: FromDishka[CreateOrderFromCartHandler],
) -> CreateOrderResponse:
    result = await handler.handle(
        CreateOrderFromCartCommand(
            identity_id=auth.identity_id,
            cart_id=body.cart_id,
            snapshot_id=body.snapshot_id,
            idempotency_key=body.idempotency_key,
            payment_provider=body.payment_provider,
            delivery_quote_id=body.delivery_quote_id,
        )
    )
    return CreateOrderResponse(
        order_id=result.order_id,
        payment_intent_id=result.payment_intent_id,
        client_secret=result.client_secret,
        total_amount=result.total_amount,
        currency=result.currency,
    )


@order_router.get("", response_model=CustomerOrderListResponse)
async def list_my_orders(
    auth: Auth,
    handler: FromDishka[ListMyOrdersHandler],
    limit: int = Query(default=20, ge=1, le=100),
    cursor: datetime | None = Query(default=None),
) -> CustomerOrderListResponse:
    page = await handler.handle(
        ListMyOrdersQuery(identity_id=auth.identity_id, limit=limit, cursor=cursor)
    )
    return CustomerOrderListResponse(
        items=[_serialize(o) for o in page.items],
        next_cursor=page.next_cursor,
    )


@order_router.get("/{orderId}", response_model=CustomerOrderSchema)
async def get_order(
    order_id: Annotated[uuid.UUID, Path(alias="orderId")],
    auth: Auth,
    handler: FromDishka[GetOrderHandler],
) -> CustomerOrderSchema:
    rm = await handler.handle(
        GetOrderQuery(order_id=order_id, identity_id=auth.identity_id)
    )
    return _serialize(rm)


@order_router.get("/{orderId}/tracking", response_model=OrderTrackingResponse)
async def get_order_tracking(
    order_id: Annotated[uuid.UUID, Path(alias="orderId")],
    auth: Auth,
    handler: FromDishka[GetOrderTrackingHandler],
) -> OrderTrackingResponse:
    """Aggregated tracking page: dual-leg tracking numbers + timeline.

    Combines the Chinese ``incoming_declaration``, the DobroPost
    ``dpTrackNumber`` (cross-border), and the russian-carrier last-mile
    track. Returns a chronologically ordered list of steps so the
    front-end can render the journey without additional joins.
    """
    rm = await handler.handle(
        GetOrderTrackingQuery(order_id=order_id, identity_id=auth.identity_id)
    )
    return OrderTrackingResponse(
        order_id=rm.order_id,
        order_number=rm.order_number,
        status=rm.status,
        raw_status=rm.raw_status,
        incoming_declaration=rm.incoming_declaration,
        cross_border_track=rm.cross_border_track,
        last_mile_track=rm.last_mile_track,
        cross_border_status_id=rm.cross_border_status_id,
        cross_border_status_label=rm.cross_border_status_label,
        steps=[
            TrackingStepSchema(
                occurred_at=s.occurred_at,
                code=s.code,
                label=s.label,
                leg=s.leg,
            )
            for s in rm.steps
        ],
    )


@order_router.post("/{orderId}/cancel", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_order(
    order_id: Annotated[uuid.UUID, Path(alias="orderId")],
    body: CancelOrderRequest,
    auth: Auth,
    handler: FromDishka[CancelOrderHandler],
) -> None:
    try:
        reason = CancellationReason(body.reason)
    except ValueError:
        reason = CancellationReason.CUSTOMER_CHANGED_MIND
    await handler.handle(
        CancelOrderCommand(
            order_id=order_id,
            identity_id=auth.identity_id,
            reason=reason,
            actor_id=str(auth.identity_id),
            idempotency_key=body.idempotency_key,
        )
    )


@order_router.post(
    "/{orderId}/refresh-recipient", status_code=status.HTTP_204_NO_CONTENT
)
async def refresh_recipient(
    order_id: Annotated[uuid.UUID, Path(alias="orderId")],
    auth: Auth,
    handler: FromDishka[RefreshRecipientSnapshotHandler],
) -> None:
    """Re-snapshot the recipient on an ON_HOLD order after the customer
    fixed passport details. Caller still needs to invoke ``resume`` (or
    wait for DobroPost passport-webhook) once the upstream re-validates.
    """
    await handler.handle(
        RefreshRecipientSnapshotCommand(order_id=order_id, identity_id=auth.identity_id)
    )


@order_router.patch("/{orderId}/pickup-point", status_code=status.HTTP_204_NO_CONTENT)
async def change_pickup_point(
    order_id: Annotated[uuid.UUID, Path(alias="orderId")],
    body: ChangePickupPointRequest,
    auth: Auth,
    handler: FromDishka[ChangePickupPointHandler],
) -> None:
    await handler.handle(
        ChangePickupPointCommand(
            order_id=order_id,
            identity_id=auth.identity_id,
            carrier=body.carrier,
            point_id=body.point_id,
        )
    )
