"""Manager command: PAID → PROCURED after entering Chinese tracking number.

Side effects:
1. Capture the (until now AUTHORIZED-only) PaymentIntent.
2. Book a DobroPost cross-border shipment with the supplied
   ``incoming_declaration``.
3. Move Order FSM to PROCURED.

Idempotent on ``incoming_declaration`` (UNIQUE constraint at DB level).
"""

import uuid
from dataclasses import dataclass

from src.modules.order.application._history import record_history
from src.modules.order.application.ports import (
    IDobroPostGateway,
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
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


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
        dobropost_gateway: IDobroPostGateway,
        history_writer: IOrderStateHistoryWriter,
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
        self._order_repo = order_repo
        self._payment_gateway = payment_gateway
        self._dobropost = dobropost_gateway
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

            # 2) Book DobroPost cross-border shipment.
            cross_border_shipment_id = await self._dobropost.book_cross_border(
                order_id=order.id,
                identity_id=order.identity_id,
                incoming_declaration=declaration.value,
                idempotency_key=f"order:{order.id}:dobropost",
            )

            # 3) Move FSM and persist all the new fields atomically.
            pre = order.status
            order.procure(incoming_declaration=declaration, admin_id=command.admin_id)
            order.attach_cross_border_shipment(cross_border_shipment_id)
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
                cross_border_shipment_id=str(cross_border_shipment_id),
            )
