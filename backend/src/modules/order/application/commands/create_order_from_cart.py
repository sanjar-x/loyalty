"""Command: create an order from a confirmed cart checkout snapshot.

Flow:
1. Order created in PENDING state.
2. PaymentIntent authorized (two-step) and attached to order.
3. PENDING remains until ``MarkOrderPaid`` consumer fires on
   ``PaymentCapturedEvent`` from the cron auth-expiry / capture-on-procure
   handler. **Capture deferred** until the manager procures the goods.

Idempotent through ``IIdempotencyKeyStore``.
"""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

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
    IIdempotencyKeyStore,
    IOrderRepository,
    IOrderStateHistoryWriter,
    IRecipientLookup,
)
from src.modules.order.domain.recipient_snapshot import RecipientSnapshot
from src.shared.exceptions import UnprocessableEntityError
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


@dataclass(frozen=True)
class CreateOrderFromCartResult:
    order_id: uuid.UUID
    payment_intent_id: uuid.UUID
    client_secret: str | None
    total_amount: int
    currency: str


class CreateOrderFromCartHandler:
    def __init__(
        self,
        order_repo: IOrderRepository,
        snapshot_reader: ICartSnapshotReader,
        recipient_lookup: IRecipientLookup,
        idempotency_store: IIdempotencyKeyStore,
        payment_gateway: IPaymentGateway,
        history_writer: IOrderStateHistoryWriter,
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
        self._order_repo = order_repo
        self._snapshots = snapshot_reader
        self._recipient_lookup = recipient_lookup
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
                passport_serial=recipient.passport_serial,
                passport_number=recipient.passport_number,
                passport_issue_date=recipient.passport_issue_date,
                birth_date=recipient.birth_date,
                inn=recipient.inn,
            )

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
            order = Order.create(
                identity_id=command.identity_id,
                cart_id=command.cart_id,
                items=items,
                currency=snapshot.currency,
                pickup_point=snapshot.pickup_point,
                recipient_snapshot=recipient_snapshot,
                cny_rate_at_checkout=snapshot.cny_rate_at_checkout,
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
            )
            return CreateOrderFromCartResult(
                order_id=order.id,
                payment_intent_id=ticket.intent_id,
                client_secret=ticket.client_secret,
                total_amount=order.total_amount,
                currency=order.currency,
            )
