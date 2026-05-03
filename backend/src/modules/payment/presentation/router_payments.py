"""Payment customer endpoints (under ``/payments``).

* ``GET  /payments/intents/{intent_id}`` — fetch intent details.
* ``POST /payments/intents/{intent_id}/_simulate-capture`` — dev-only
  endpoint to drive the FakePaymentProvider through capture without a
  real PSP webhook. Disabled automatically when
  ``PAYMENT_SIMULATION_ENABLED=false`` or ``ENVIRONMENT=prod``.

PSP webhook ingress (server-to-server) lives in ``router_webhooks.py``
under ``/webhooks/payments/{provider}`` per the global webhooks
namespace convention.
"""

import uuid

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, status

from src.bootstrap.config import settings
from src.modules.identity.presentation.dependencies import Auth
from src.modules.payment.application.commands.capture_payment_intent import (
    CapturePaymentIntentCommand,
    CapturePaymentIntentHandler,
)
from src.modules.payment.application.queries.get_payment_intent import (
    GetPaymentIntentHandler,
    GetPaymentIntentQuery,
)
from src.modules.payment.domain.exceptions import PaymentSimulationDisabledError
from src.modules.payment.presentation.schemas import (
    PaymentIntentSchema,
    SimulateCaptureRequest,
)

payment_router = APIRouter(
    prefix="/payments",
    tags=["Payments"],
    route_class=DishkaRoute,
)


@payment_router.get(
    "/intents/{intent_id}",
    response_model=PaymentIntentSchema,
)
async def get_payment_intent(
    intent_id: uuid.UUID,
    auth: Auth,
    handler: FromDishka[GetPaymentIntentHandler],
) -> PaymentIntentSchema:
    rm = await handler.handle(GetPaymentIntentQuery(intent_id=intent_id))
    return PaymentIntentSchema(
        intent_id=rm.intent_id,
        order_id=rm.order_id,
        provider=rm.provider,
        amount=rm.amount,
        currency=rm.currency,
        status=rm.status,
        provider_reference=rm.provider_reference,
        client_secret=rm.client_secret,
        failure_reason=rm.failure_reason,
        created_at=rm.created_at,
        updated_at=rm.updated_at,
    )


@payment_router.post(
    "/intents/{intent_id}/_simulate-capture",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def simulate_capture(
    intent_id: uuid.UUID,
    body: SimulateCaptureRequest,
    auth: Auth,
    handler: FromDishka[CapturePaymentIntentHandler],
) -> None:
    if settings.ENVIRONMENT == "prod" or not settings.PAYMENT_SIMULATION_ENABLED:
        raise PaymentSimulationDisabledError()
    await handler.handle(
        CapturePaymentIntentCommand(
            intent_id=intent_id, idempotency_key=body.idempotency_key
        )
    )
