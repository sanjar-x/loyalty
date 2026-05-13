"""PSP webhook ingress (server-to-server).

Mounted under the global ``/webhooks/*`` namespace so PSP integrations
discover it via the documented webhooks convention. Real PSP adapters
(yookassa / sbp / tinkoff) plug per-provider signature verification on
top of this entry point; the FakeProvider accepts any payload that
references a known intent_id.
"""

from __future__ import annotations

import uuid

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Body, Path, status

from src.modules.payment.application.commands.capture_payment_intent import (
    CapturePaymentIntentCommand,
    CapturePaymentIntentHandler,
)

payment_webhook_router = APIRouter(
    prefix="/webhooks/payments",
    tags=["Webhooks / Payments"],
    route_class=DishkaRoute,
)


@payment_webhook_router.post(
    "/{provider}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def provider_webhook(
    handler: FromDishka[CapturePaymentIntentHandler],
    provider: str = Path(..., max_length=32),
    payload: dict = Body(...),
) -> None:
    """Generic PSP webhook ingress.

    Real PSP integrations validate signatures via the ``provider`` field
    (per-provider middleware). The FakeProvider does not need that —
    we only require ``intent_id`` and ``idempotency_key`` in the body.
    """
    intent_id_raw = payload.get("intent_id") or payload.get("intentId")
    if not intent_id_raw:
        return
    try:
        intent_id = uuid.UUID(str(intent_id_raw))
    except TypeError, ValueError:
        return
    idem = str(payload.get("idempotency_key") or f"webhook:{provider}:{intent_id}")
    await handler.handle(
        CapturePaymentIntentCommand(intent_id=intent_id, idempotency_key=idem)
    )
