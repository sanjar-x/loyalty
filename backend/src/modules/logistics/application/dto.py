"""
Application-layer DTOs for the logistics module.

These frozen dataclasses bridge domain value objects and
command/query handlers when the domain VOs are too rich or
when a simpler shape is needed for handler I/O.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime

from src.modules.logistics.domain.value_objects import (
    DeliveryQuote,
)


@dataclass(frozen=True)
class CalculateRatesResult:
    """Aggregated result of a rate fan-out query.

    Attributes:
        quotes: Successfully retrieved quotes (with provider payload).
        errors: Per-provider errors for providers that failed.
    """

    quotes: list[DeliveryQuote]
    errors: dict[str, str]  # provider_code → error message


@dataclass(frozen=True)
class ShipmentSummary:
    """Lightweight read model for shipment listings."""

    id: uuid.UUID
    order_id: uuid.UUID | None
    provider_code: str
    service_code: str
    delivery_type: str
    status: str
    tracking_number: str | None
    latest_tracking_status: str | None
    quoted_cost_amount: int
    quoted_cost_currency: str
    created_at: datetime
    updated_at: datetime
