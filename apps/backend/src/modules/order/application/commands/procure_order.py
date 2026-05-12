"""Manager command: PAID → PROCURED after entering Chinese tracking number.

ORD-006 (D1.2) — DobroPost booking is now async via the outbox.
Pre-fix the handler called ``dobropost.book_cross_border`` synchronously,
which left a split-state risk: capture succeeded, DobroPost down →
order stuck in PAID with no shipment + manual refund.

Post-fix synchronous side effects (all atomic in one UoW):

1. Capture the (until now AUTHORIZED-only) PaymentIntent.
2. Move Order FSM to PROCURED + emit ``OrderProcuredEvent``.

The ``OrderProcuredConsumer`` (subscribed via the outbox) then books
the DobroPost shipment with TaskIQ retry + circuit breaker. On
exhausted retries → ``HoldOrder(reason=BOOKING_FAILED)`` so the
manager can triage from the admin dashboard.

Idempotent on ``incoming_declaration`` (UNIQUE constraint at DB level).
"""

import uuid
from dataclasses import dataclass

from src.modules.order.application._history import record_history
from src.modules.order.application.ports import (
    IPaymentGateway,
)
from src.modules.order.domain.exceptions import (
    IncomingDeclarationConflictError,
    OrderInvalidTransitionError,
    OrderNotFoundError,
)
from src.modules.order.domain.interfaces import (
    HistoryActor,
    IOrderRepository,
    IOrderStateHistoryWriter,
)
from src.modules.order.domain.value_objects import (
    IncomingDeclaration,
    OrderStatus,
)
from shared.interfaces.logger import ILogger
from shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class ProcureOrderCommand:
    order_id: uuid.UUID
    incoming_declaration: str
    admin_id: uuid.UUID


class ProcureOrderHandler:
    def __init__(
        self,
        order_repo: IOrderRepository,
        payment_gateway: IPaymentGateway,
        history_writer: IOrderStateHistoryWriter,
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
        self._order_repo = order_repo
        self._payment_gateway = payment_gateway
        self._history = history_writer
        self._uow = uow
        self._logger = logger.bind(handler="ProcureOrderHandler")

    async def handle(self, command: ProcureOrderCommand) -> None:
        async with self._uow:
            order = await self._order_repo.get_for_update(command.order_id)
            if order is None:
                raise OrderNotFoundError(order_id=str(command.order_id))
            if order.status != OrderStatus.PAID:
                raise OrderInvalidTransitionError(
                    current=order.status.value, target=OrderStatus.PROCURED.value
                )

            declaration = IncomingDeclaration.parse(command.incoming_declaration)

            # Idempotency by natural key — UNIQUE on orders.incoming_declaration
            existing = await self._order_repo.get_by_incoming_declaration(
                declaration.value
            )
            if existing is not None and existing.id != order.id:
                raise IncomingDeclarationConflictError(declaration=declaration.value)
            if (
                order.incoming_declaration is not None
                and order.incoming_declaration.value == declaration.value
            ):
                # Already procured with this declaration — no-op.
                return

            # 1) Capture funds.
            if order.payment_intent_id is None:
                raise OrderInvalidTransitionError(
                    current=order.status.value, target="capture (no payment intent)"
                )
            await self._payment_gateway.capture(
                intent_id=order.payment_intent_id,
                idempotency_key=f"order:{order.id}:capture",
            )

            # 2) Move FSM. ``OrderProcuredEvent`` lands in the outbox
            # via ``register_aggregate(order)`` + ``commit()``; the
            # ``OrderProcuredConsumer`` then books DobroPost + attaches
            # ``cross_border_shipment_id`` asynchronously.
            pre = order.status
            order.procure(incoming_declaration=declaration, admin_id=command.admin_id)
            await self._order_repo.update(order)
            await record_history(
                order=order,
                history_writer=self._history,
                actor=HistoryActor(
                    actor_type="manager", actor_id=str(command.admin_id)
                ),
                pre_commit_status=pre,
            )
            self._uow.register_aggregate(order)
            await self._uow.commit()

            self._logger.info(
                "order.procured",
                order_id=str(order.id),
                admin_id=str(command.admin_id),
                incoming_declaration=declaration.value,
            )
