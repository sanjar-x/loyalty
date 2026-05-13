"""ACL adapter: order → payment.

The only file in the order module allowed to import the payment module.
Routes Order's calls through Payment's public command handlers — no
Payment ORM access. Implements the new ``IPaymentGateway`` port from
``src.modules.order.application.ports`` (two-step authorize+capture).
"""

import uuid

from src.modules.order.application.ports import IPaymentGateway, PaymentTicket
from src.modules.payment.application.commands.capture_payment_intent import (
    CapturePaymentIntentCommand,
    CapturePaymentIntentHandler,
)
from src.modules.payment.application.commands.create_payment_intent import (
    CreatePaymentIntentCommand,
    CreatePaymentIntentHandler,
)
from src.modules.payment.application.commands.refund_payment_intent import (
    RefundPaymentIntentCommand,
    RefundPaymentIntentHandler,
)
from src.modules.payment.domain.value_objects import ProviderCode


class PaymentGateway(IPaymentGateway):
    def __init__(
        self,
        create_handler: CreatePaymentIntentHandler,
        capture_handler: CapturePaymentIntentHandler,
        refund_handler: RefundPaymentIntentHandler,
    ) -> None:
        self._create = create_handler
        self._capture = capture_handler
        self._refund = refund_handler

    async def authorize(
        self,
        *,
        order_id: uuid.UUID,
        identity_id: uuid.UUID,
        amount: int,
        currency: str,
        idempotency_key: str,
        provider: str,
    ) -> PaymentTicket:
        try:
            provider_code = ProviderCode(provider)
        except ValueError:
            provider_code = ProviderCode.FAKE
        result = await self._create.handle(
            CreatePaymentIntentCommand(
                order_id=order_id,
                amount=amount,
                currency=currency,
                idempotency_key=idempotency_key,
                provider=provider_code,
            )
        )
        return PaymentTicket(
            intent_id=result.intent_id, client_secret=result.client_secret
        )

    async def capture(self, *, intent_id: uuid.UUID, idempotency_key: str) -> None:
        await self._capture.handle(
            CapturePaymentIntentCommand(
                intent_id=intent_id, idempotency_key=idempotency_key
            )
        )

    async def refund(self, *, intent_id: uuid.UUID, idempotency_key: str) -> None:
        await self._refund.handle(
            RefundPaymentIntentCommand(
                intent_id=intent_id, idempotency_key=idempotency_key
            )
        )
