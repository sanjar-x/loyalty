"""Command: create an order from a confirmed cart checkout snapshot.

Flow:
1. Order created in PENDING state.
2. PaymentIntent authorized (two-step) and attached to order.
3. PENDING remains until ``MarkOrderPaid`` consumer fires on
   ``PaymentCapturedEvent`` from the cron auth-expiry / capture-on-procure
   handler. **Capture deferred** until the manager procures the goods.

Idempotent through ``IIdempotencyStore`` from the shared kernel
(``src.shared.interfaces.idempotency``).
"""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from src.bootstrap.config import settings
from src.modules.order.application._delivery import resolve_delivery_quote
from src.modules.order.application._history import record_history
from src.modules.order.application.ports import IPaymentGateway
from src.modules.order.domain.entities import Order, OrderItem
from src.modules.order.domain.exceptions import (
    IdempotencyKeyConflictError,
    OrderEmptyError,
)
from src.modules.order.domain.interfaces import (
    HistoryActor,
    ICartSnapshotReader,
    IDeliveryQuoteLookup,
    IOrderRepository,
    IOrderStateHistoryWriter,
    IPassportLookup,
    IRecipientLookup,
)
from src.modules.order.domain.recipient_snapshot import (
    PassportSnapshot,
    RecipientSnapshot,
)
from src.shared.exceptions import UnprocessableEntityError
from src.shared.interfaces.idempotency import IIdempotencyStore
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork

IDEMPOTENCY_TTL_HOURS = 24
SCOPE = "order.create"


@dataclass(frozen=True)
class CreateOrderFromCartCommand:
    identity_id: uuid.UUID
    cart_id: uuid.UUID
    snapshot_id: uuid.UUID
    idempotency_key: str
    payment_provider: str = "fake"
    # Server-trusted quote id returned by
    # ``/storefront/logistics/rates/quote``. When supplied, the handler
    # resolves the priced amount through ``IDeliveryQuoteLookup`` and
    # bakes it into ``Order.delivery_amount`` so the payment hold covers
    # goods + shipping. Optional so legacy clients that pre-date the
    # checkout-quote step keep working — they ship an order without a
    # priced shipping line.
    delivery_quote_id: uuid.UUID | None = None
    # ADR-011 / Sprint 1.5 Part 2 — explicit passport selection at
    # cart-checkout. Same semantics as Buy Now: required at handler
    # level when any cart item is CROSS_BORDER, optional otherwise.
    passport_id: uuid.UUID | None = None


@dataclass(frozen=True)
class CreateOrderFromCartResult:
    order_id: uuid.UUID
    payment_intent_id: uuid.UUID
    client_secret: str | None
    total_amount: int
    currency: str
    # True when ``settings.PAYMENT_AUTO_CAPTURE_ON_AUTHORIZE`` short-
    # circuited the PSP roundtrip and the Order is already PAID at
    # response time. Frontend uses this to skip the payment widget /
    # redirect and navigate straight to "оформлено" instead of polling
    # PaymentIntent status. When False — fall back to the normal
    # client_secret + PSP-confirmation flow.
    auto_captured: bool = False


class CreateOrderFromCartHandler:
    def __init__(
        self,
        order_repo: IOrderRepository,
        snapshot_reader: ICartSnapshotReader,
        recipient_lookup: IRecipientLookup,
        passport_lookup: IPassportLookup,
        delivery_quote_lookup: IDeliveryQuoteLookup,
        idempotency_store: IIdempotencyStore,
        payment_gateway: IPaymentGateway,
        history_writer: IOrderStateHistoryWriter,
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
        self._order_repo = order_repo
        self._snapshots = snapshot_reader
        self._recipient_lookup = recipient_lookup
        self._passport_lookup = passport_lookup
        self._delivery_quote_lookup = delivery_quote_lookup
        self._idem = idempotency_store
        self._gateway = payment_gateway
        self._history = history_writer
        self._uow = uow
        self._logger = logger.bind(handler="CreateOrderFromCartHandler")

    async def handle(
        self, command: CreateOrderFromCartCommand
    ) -> CreateOrderFromCartResult:
        async with self._uow:
            existing_id = await self._idem.get_result(
                key=command.idempotency_key, scope=SCOPE
            )
            if existing_id is not None:
                order = await self._order_repo.get(existing_id)
                if order is None or order.payment_intent_id is None:
                    raise IdempotencyKeyConflictError()
                # Re-fetch existing payment ticket via a no-op authorize
                # call (idempotency on the payment side returns the same
                # intent_id + client_secret).
                ticket = await self._gateway.authorize(
                    order_id=order.id,
                    identity_id=order.identity_id,
                    amount=order.total_amount,
                    currency=order.currency,
                    idempotency_key=f"order:{order.id}:auth",
                    provider=command.payment_provider,
                )
                return CreateOrderFromCartResult(
                    order_id=order.id,
                    payment_intent_id=ticket.intent_id,
                    client_secret=ticket.client_secret,
                    total_amount=order.total_amount,
                    currency=order.currency,
                    auto_captured=order.was_paid,
                )

            snapshot = await self._snapshots.get(
                cart_id=command.cart_id, snapshot_id=command.snapshot_id
            )
            if snapshot is None or not snapshot.items:
                raise OrderEmptyError()

            recipient = await self._recipient_lookup.get(snapshot.recipient_id)
            if recipient is None or recipient.is_archived:
                raise UnprocessableEntityError(
                    message="Recipient not found or archived",
                    error_code="ORDER_RECIPIENT_INVALID",
                    details={"recipient_id": str(snapshot.recipient_id)},
                )
            if recipient.identity_id != command.identity_id:
                # Cart-side check should have caught this — fail safe here.
                raise UnprocessableEntityError(
                    message="Recipient does not belong to this customer",
                    error_code="ORDER_RECIPIENT_OWNERSHIP_MISMATCH",
                )

            recipient_snapshot = RecipientSnapshot(
                recipient_id=str(recipient.recipient_id),
                full_name_ru=recipient.full_name_ru,
                full_name_lat=recipient.full_name_lat,
                phone=recipient.phone,
                email=recipient.email,
            )

            # ADR-011 — passport lookup + ownership check (same pattern
            # as Buy Now handler). Optional; Order.create invariant
            # raises 422 PASSPORT_REQUIRED_FOR_CROSS_BORDER when the
            # cart has CROSS_BORDER items but no passport was provided.
            passport_snapshot: PassportSnapshot | None = None
            passport_id: uuid.UUID | None = None
            if command.passport_id is not None:
                passport = await self._passport_lookup.get(command.passport_id)
                if passport is None or passport.is_archived:
                    raise UnprocessableEntityError(
                        message="Passport not found or archived",
                        error_code="ORDER_PASSPORT_INVALID",
                        details={"passport_id": str(command.passport_id)},
                    )
                if passport.identity_id != command.identity_id:
                    raise UnprocessableEntityError(
                        message="Passport does not belong to this customer",
                        error_code="ORDER_PASSPORT_OWNERSHIP_MISMATCH",
                        details={"passport_id": str(command.passport_id)},
                    )
                passport_snapshot = PassportSnapshot(
                    passport_id=str(passport.passport_id),
                    full_name_ru=passport.full_name_ru,
                    full_name_lat=passport.full_name_lat,
                    passport_serial=passport.passport_serial,
                    passport_number=passport.passport_number,
                    passport_issue_date=passport.passport_issue_date,
                    birth_date=passport.birth_date,
                    inn=passport.inn,
                    validation_status=passport.validation_status,
                )
                passport_id = passport.passport_id

            items = [
                OrderItem(
                    id=uuid.uuid4(),
                    sku_id=s.sku_id,
                    product_id=s.product_id,
                    variant_id=s.variant_id,
                    product_name=s.product_name,
                    variant_label=s.variant_label,
                    supplier_type=s.supplier_type,
                    quantity=s.quantity,
                    unit_price_amount=s.unit_price_amount,
                    currency=s.currency,
                )
                for s in snapshot.items
            ]
            delivery_amount, delivery_quote_id = await resolve_delivery_quote(
                quote_id=command.delivery_quote_id,
                identity_id=command.identity_id,
                expected_currency=snapshot.currency,
                lookup=self._delivery_quote_lookup,
            )
            order = Order.create(
                identity_id=command.identity_id,
                cart_id=command.cart_id,
                items=items,
                currency=snapshot.currency,
                pickup_point=snapshot.pickup_point,
                recipient_snapshot=recipient_snapshot,
                cny_rate_at_checkout=snapshot.cny_rate_at_checkout,
                delivery_quote_id=delivery_quote_id,
                delivery_amount=delivery_amount,
                passport_id=passport_id,
                passport_snapshot=passport_snapshot,
            )
            # Brand-new aggregate: history pre-commit status is None — the
            # OrderCreatedEvent is the first transition.
            order = await self._order_repo.add(order)
            await record_history(
                order=order,
                history_writer=self._history,
                actor=HistoryActor(
                    actor_type="customer", actor_id=str(command.identity_id)
                ),
                pre_commit_status=None,
            )

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

            # Skip-payment short-circuit (settings.PAYMENT_AUTO_CAPTURE_ON_AUTHORIZE).
            # Capture the just-created PaymentIntent inside the same UoW
            # and walk Order PENDING → PAID right here, so customer flow
            # works without a PSP integration. Gateway.capture is
            # idempotent via ``order:<id>:capture-on-create`` key; the
            # downstream PaymentCapturedEvent → ``MarkOrderPaidConsumer``
            # path stays valid but becomes a no-op (mark_paid on an
            # already-PAID order returns early via FSM guard).
            paid_via_skip = False
            if settings.PAYMENT_AUTO_CAPTURE_ON_AUTHORIZE:
                await self._gateway.capture(
                    intent_id=ticket.intent_id,
                    idempotency_key=f"order:{order.id}:capture-on-create",
                )
                order.mark_paid(payment_intent_id=ticket.intent_id)
                await self._order_repo.update(order)
                paid_via_skip = True

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
                "order.created",
                order_id=str(order.id),
                cart_id=str(command.cart_id),
                total_amount=order.total_amount,
                currency=order.currency,
                payment_intent_id=str(ticket.intent_id),
                paid_via_skip_payment=paid_via_skip,
            )
            return CreateOrderFromCartResult(
                order_id=order.id,
                payment_intent_id=ticket.intent_id,
                client_secret=ticket.client_secret,
                total_amount=order.total_amount,
                currency=order.currency,
                auto_captured=paid_via_skip,
            )
