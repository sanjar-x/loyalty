"""Command: customer creates an order directly from a single SKU (Buy Now).

Bypasses the cart pipeline — the customer hits "Купить сейчас" on a
product page and the front-end POSTs the SKU + recipient + pickup +
delivery_quote in one request. Semantically identical to
``CreateOrderFromCart`` from the FSM's point of view (PENDING → PAID →
PROCURED → ...): same payment-flow, same outbox fan-out, same
Telegram notifications, same DobroPost booking on procurement.

Differences vs. cart-flow:

* No ``CartCheckoutSnapshot`` — the handler assembles a single
  :class:`OrderItem` from a catalog SKU snapshot
  (:class:`ICatalogSkuPriceReader`, reused from the walk-in flow).
* ``Order.cart_id`` is a phantom UUID (same trick as walk-in; the
  column is a soft link, not a FK — see ``OrderModel.cart_id``).
* ``is_walk_in`` stays ``False`` — this is a normal customer order, so
  ``refresh_recipient_snapshot`` works (the customer owns the
  Recipient row that was passed in).

Idempotent through ``IIdempotencyStore`` with scope
``"order.create_buy_now"``. A retry with the same key short-circuits to
the previously-created order.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from src.bootstrap.config import settings
from src.modules.order.application._delivery import resolve_delivery_quote
from src.modules.order.application._history import record_history
from src.modules.order.application.ports import (
    ICatalogSkuPriceReader,
    IPaymentGateway,
)
from src.modules.order.domain.entities import Order, OrderItem
from src.modules.order.domain.exceptions import (
    IdempotencyKeyConflictError,
)
from src.modules.order.domain.interfaces import (
    HistoryActor,
    IDeliveryQuoteLookup,
    IOrderRepository,
    IOrderStateHistoryWriter,
    IRecipientLookup,
)
from src.modules.order.domain.recipient_snapshot import RecipientSnapshot
from src.modules.order.domain.value_objects import PickupPointPreference
from src.shared.domain.supplier_type import SupplierType
from src.shared.exceptions import UnprocessableEntityError
from src.shared.interfaces.idempotency import IIdempotencyStore
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork

IDEMPOTENCY_TTL_HOURS = 24
SCOPE = "order.create_buy_now"


@dataclass(frozen=True)
class CreateBuyNowOrderCommand:
    """Inputs for the Buy Now command.

    ``payment_provider`` defaults to ``"fake"`` so the customer-flow
    works while no real PSP is wired (mirrors ``CreateOrderFromCart``).
    """

    identity_id: uuid.UUID
    sku_id: uuid.UUID
    quantity: int
    recipient_id: uuid.UUID
    pickup_point: PickupPointPreference
    delivery_quote_id: uuid.UUID | None
    idempotency_key: str
    payment_provider: str = "fake"


@dataclass(frozen=True)
class CreateBuyNowOrderResult:
    order_id: uuid.UUID
    payment_intent_id: uuid.UUID
    client_secret: str | None
    total_amount: int
    currency: str
    # See ``CreateOrderFromCartResult.auto_captured`` — same semantics.
    # When True the Order is already PAID at response time; front-end
    # should skip the PSP redirect and navigate straight to the order
    # detail page.
    auto_captured: bool = False


class CreateBuyNowOrderHandler:
    def __init__(
        self,
        order_repo: IOrderRepository,
        sku_reader: ICatalogSkuPriceReader,
        recipient_lookup: IRecipientLookup,
        delivery_quote_lookup: IDeliveryQuoteLookup,
        idempotency_store: IIdempotencyStore,
        payment_gateway: IPaymentGateway,
        history_writer: IOrderStateHistoryWriter,
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
        self._order_repo = order_repo
        self._sku_reader = sku_reader
        self._recipient_lookup = recipient_lookup
        self._delivery_quote_lookup = delivery_quote_lookup
        self._idem = idempotency_store
        self._gateway = payment_gateway
        self._history = history_writer
        self._uow = uow
        self._logger = logger.bind(handler="CreateBuyNowOrderHandler")

    async def handle(
        self, command: CreateBuyNowOrderCommand
    ) -> CreateBuyNowOrderResult:
        async with self._uow:
            # 1) Idempotency replay — short-circuit identically to
            # CreateOrderFromCart so a UI double-submit returns the
            # same order + a re-fetched payment ticket.
            existing_id = await self._idem.get_result(
                key=command.idempotency_key, scope=SCOPE
            )
            if existing_id is not None:
                order = await self._order_repo.get(existing_id)
                if order is None or order.payment_intent_id is None:
                    raise IdempotencyKeyConflictError()
                ticket = await self._gateway.authorize(
                    order_id=order.id,
                    identity_id=order.identity_id,
                    amount=order.total_amount,
                    currency=order.currency,
                    idempotency_key=f"order:{order.id}:auth",
                    provider=command.payment_provider,
                )
                return CreateBuyNowOrderResult(
                    order_id=order.id,
                    payment_intent_id=ticket.intent_id,
                    client_secret=ticket.client_secret,
                    total_amount=order.total_amount,
                    currency=order.currency,
                    auto_captured=order.was_paid,
                )

            # 2) Snapshot SKU + parent metadata in one round-trip.
            snapshots = await self._sku_reader.get_many((command.sku_id,), locale="ru")
            snap = snapshots.get(command.sku_id)
            if snap is None:
                raise UnprocessableEntityError(
                    message="SKU not found",
                    error_code="BUY_NOW_SKU_NOT_FOUND",
                    details={"sku_id": str(command.sku_id)},
                )
            if not snap.is_active:
                raise UnprocessableEntityError(
                    message="SKU is not active",
                    error_code="BUY_NOW_SKU_INACTIVE",
                    details={"sku_id": str(command.sku_id)},
                )
            if snap.selling_price_amount is None:
                # ADR-005 — selling_price is set by the autonomous
                # recompute pipeline. None means the SKU is in
                # ``status=legacy`` with no priced computation yet.
                raise UnprocessableEntityError(
                    message="SKU is not priced yet",
                    error_code="BUY_NOW_SKU_UNPRICED",
                    details={"sku_id": str(command.sku_id)},
                )

            # 3) Recipient ownership + archive check — same boundary
            # asserted at the cart side, re-asserted here so a buy-now
            # path cannot bypass it.
            recipient = await self._recipient_lookup.get(command.recipient_id)
            if recipient is None or recipient.is_archived:
                raise UnprocessableEntityError(
                    message="Recipient not found or archived",
                    error_code="ORDER_RECIPIENT_INVALID",
                    details={"recipient_id": str(command.recipient_id)},
                )
            if recipient.identity_id != command.identity_id:
                raise UnprocessableEntityError(
                    message="Recipient does not belong to this customer",
                    error_code="ORDER_RECIPIENT_OWNERSHIP_MISMATCH",
                    details={"recipient_id": str(command.recipient_id)},
                )

            recipient_snapshot = RecipientSnapshot(
                recipient_id=str(recipient.recipient_id),
                full_name_ru=recipient.full_name_ru,
                full_name_lat=recipient.full_name_lat,
                phone=recipient.phone,
                email=recipient.email,
                passport_serial=recipient.passport_serial,
                passport_number=recipient.passport_number,
                passport_issue_date=recipient.passport_issue_date,
                birth_date=recipient.birth_date,
                inn=recipient.inn,
            )

            # 4) Build one OrderItem.
            item = OrderItem(
                id=uuid.uuid4(),
                sku_id=snap.sku_id,
                product_id=snap.product_id,
                variant_id=snap.variant_id,
                product_name=snap.product_name,
                variant_label=snap.variant_label,
                supplier_type=SupplierType(snap.supplier_type),
                quantity=command.quantity,
                unit_price_amount=snap.selling_price_amount,
                currency=snap.currency,
            )

            # 5) Resolve delivery quote (shared with cart-flow).
            delivery_amount, delivery_quote_id = await resolve_delivery_quote(
                quote_id=command.delivery_quote_id,
                identity_id=command.identity_id,
                expected_currency=snap.currency,
                lookup=self._delivery_quote_lookup,
            )

            # 6) Order.create with phantom cart_id. Buy-now is a
            # customer order without a backing cart row; the cart_id
            # column is a soft link (no FK), and analytics that need
            # to tell the two flows apart should rely on a future
            # ``Order.creation_source`` discriminator rather than
            # heuristics over cart_id (which would also misclassify
            # walk-in orders).
            phantom_cart_id = uuid.uuid4()
            order = Order.create(
                identity_id=command.identity_id,
                cart_id=phantom_cart_id,
                items=[item],
                currency=snap.currency,
                pickup_point=command.pickup_point,
                recipient_snapshot=recipient_snapshot,
                delivery_quote_id=delivery_quote_id,
                delivery_amount=delivery_amount,
            )
            order = await self._order_repo.add(order)
            await record_history(
                order=order,
                history_writer=self._history,
                actor=HistoryActor(
                    actor_type="customer", actor_id=str(command.identity_id)
                ),
                pre_commit_status=None,
            )

            # 7) Payment authorize (two-step). Capture is deferred
            # until manager procures the goods — identical to the
            # cart-flow lifecycle.
            ticket = await self._gateway.authorize(
                order_id=order.id,
                identity_id=order.identity_id,
                amount=order.total_amount,
                currency=order.currency,
                idempotency_key=f"order:{order.id}:auth",
                provider=command.payment_provider,
            )
            order.attach_payment_intent(ticket.intent_id)
            await self._order_repo.update(order)

            # 8) Skip-payment short-circuit
            # (settings.PAYMENT_AUTO_CAPTURE_ON_AUTHORIZE). Capture +
            # mark_paid in the same UoW so customer-flow works without
            # a PSP integration; the downstream PaymentCaptured →
            # MarkOrderPaid consumer stays valid and becomes a no-op
            # via the FSM guard on already-PAID orders.
            paid_via_skip = False
            if settings.PAYMENT_AUTO_CAPTURE_ON_AUTHORIZE:
                await self._gateway.capture(
                    intent_id=ticket.intent_id,
                    idempotency_key=f"order:{order.id}:capture-on-create",
                )
                order.mark_paid(payment_intent_id=ticket.intent_id)
                await self._order_repo.update(order)
                paid_via_skip = True

            # 9) Idempotency commit.
            now = datetime.now(UTC)
            reserved = await self._idem.reserve(
                key=command.idempotency_key,
                identity_id=command.identity_id,
                scope=SCOPE,
                expires_at=now + timedelta(hours=IDEMPOTENCY_TTL_HOURS),
            )
            if not reserved:
                raise IdempotencyKeyConflictError()
            await self._idem.attach_result(
                key=command.idempotency_key,
                scope=SCOPE,
                resource_id=order.id,
            )

            self._uow.register_aggregate(order)
            await self._uow.commit()

            self._logger.info(
                "buy_now_order.created",
                order_id=str(order.id),
                identity_id=str(command.identity_id),
                sku_id=str(command.sku_id),
                quantity=command.quantity,
                total_amount=order.total_amount,
                currency=order.currency,
                payment_intent_id=str(ticket.intent_id),
                paid_via_skip_payment=paid_via_skip,
            )
            return CreateBuyNowOrderResult(
                order_id=order.id,
                payment_intent_id=ticket.intent_id,
                client_secret=ticket.client_secret,
                total_amount=order.total_amount,
                currency=order.currency,
                auto_captured=paid_via_skip,
            )
