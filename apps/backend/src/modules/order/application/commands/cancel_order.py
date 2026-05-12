"""Cancel an order (taxonomized reason).

If the order was already paid (PAID/PROCURED/ON_HOLD), the payment is
refunded *first*; only on a successful refund does the FSM transition
proceed (forward-going compensation, research (7) §9).
"""

import uuid
from dataclasses import dataclass

from src.modules.order.application._history import record_history
from src.modules.order.application.ports import IPaymentGateway
from src.modules.order.domain.exceptions import OrderNotFoundError
from src.modules.order.domain.interfaces import (
    HistoryActor,
    IOrderRepository,
    IOrderStateHistoryWriter,
)
from src.modules.order.domain.value_objects import CancellationReason
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class CancelOrderCommand:
    order_id: uuid.UUID
    identity_id: uuid.UUID | None
    reason: CancellationReason
    actor_id: str
    idempotency_key: str


class CancelOrderHandler:
    def __init__(
        self,
        order_repo: IOrderRepository,
        payment_gateway: IPaymentGateway,
        history_writer: IOrderStateHistoryWriter,
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
        self._order_repo = order_repo
        self._gateway = payment_gateway
        self._history = history_writer
        self._uow = uow
        self._logger = logger.bind(handler="CancelOrderHandler")

    async def handle(self, command: CancelOrderCommand) -> None:
        async with self._uow:
            order = await self._order_repo.get_for_update(command.order_id)
            if order is None:
                raise OrderNotFoundError(order_id=str(command.order_id))
            if (
                command.identity_id is not None
                and order.identity_id != command.identity_id
            ):
                raise OrderNotFoundError(order_id=str(command.order_id))

            refund_required = order.was_paid
            if refund_required and order.payment_intent_id is not None:
                await self._gateway.refund(
                    intent_id=order.payment_intent_id,
                    idempotency_key=f"refund:{command.idempotency_key}",
                )

            pre = order.status
            order.cancel(reason=command.reason, actor_id=command.actor_id)
            await self._order_repo.update(order)
            actor_type = "customer" if command.identity_id is not None else "system"
            actor_id = command.actor_id or (
                str(command.identity_id)
                if command.identity_id is not None
                else "system"
            )
            await record_history(
                order=order,
                history_writer=self._history,
                actor=HistoryActor(actor_type=actor_type, actor_id=actor_id),
                pre_commit_status=pre,
            )
            self._uow.register_aggregate(order)
            await self._uow.commit()
            self._logger.info(
                "order.cancelled",
                order_id=str(order.id),
                reason=command.reason.value,
                refund_required=refund_required,
            )
