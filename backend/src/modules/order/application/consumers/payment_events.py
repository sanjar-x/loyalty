"""Order consumers — payment event bridge."""

import uuid

from src.modules.order.application.commands.cancel_order import (
    CancelOrderCommand,
    CancelOrderHandler,
)
from src.modules.order.application.commands.mark_order_paid import (
    MarkOrderPaidCommand,
    MarkOrderPaidHandler,
)
from src.modules.order.domain.exceptions import OrderNotFoundError
from src.modules.order.domain.value_objects import CancellationReason
from src.shared.interfaces.logger import ILogger


class PaymentCapturedConsumer:
    def __init__(self, paid_handler: MarkOrderPaidHandler, logger: ILogger) -> None:
        self._paid_handler = paid_handler
        self._logger = logger.bind(consumer="PaymentCapturedConsumer")

    async def handle(self, payload: dict) -> None:
        try:
            order_uuid = uuid.UUID(str(payload["order_id"]))
            intent_uuid = uuid.UUID(str(payload["intent_id"]))
        except KeyError, TypeError, ValueError:
            self._logger.warning("payment.captured.skip", reason="bad_payload")
            return
        try:
            await self._paid_handler.handle(
                MarkOrderPaidCommand(order_id=order_uuid, payment_intent_id=intent_uuid)
            )
        except OrderNotFoundError:
            self._logger.warning("payment.captured.skip", reason="order_missing")


class PaymentFailedConsumer:
    def __init__(self, cancel_handler: CancelOrderHandler, logger: ILogger) -> None:
        self._cancel_handler = cancel_handler
        self._logger = logger.bind(consumer="PaymentFailedConsumer")

    async def handle(self, payload: dict) -> None:
        try:
            order_uuid = uuid.UUID(str(payload["order_id"]))
        except KeyError, TypeError, ValueError:
            self._logger.warning("payment.failed.skip", reason="bad_payload")
            return
        intent_id = str(payload.get("intent_id", ""))
        try:
            await self._cancel_handler.handle(
                CancelOrderCommand(
                    order_id=order_uuid,
                    identity_id=None,
                    reason=CancellationReason.SYSTEM_PAYMENT_FAILED,
                    actor_id="payment-service",
                    idempotency_key=f"payment-failed:{intent_id}",
                )
            )
        except OrderNotFoundError:
            self._logger.warning("payment.failed.skip", reason="order_missing")
