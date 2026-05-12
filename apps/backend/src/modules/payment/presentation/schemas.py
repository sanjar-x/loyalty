"""Pydantic schemas for payment endpoints."""

import uuid
from datetime import datetime

from pydantic import Field

from shared.schemas import CamelModel


class PaymentIntentSchema(CamelModel):
    intent_id: uuid.UUID
    order_id: uuid.UUID
    provider: str
    amount: int
    currency: str
    status: str
    provider_reference: str | None
    client_secret: str | None
    failure_reason: str | None
    created_at: datetime
    updated_at: datetime


class SimulateCaptureRequest(CamelModel):
    idempotency_key: str = Field(min_length=8, max_length=128)
