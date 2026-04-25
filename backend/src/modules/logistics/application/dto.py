"""
Application-layer DTOs for the logistics module.

These frozen dataclasses bridge domain value objects and
command/query handlers when the domain VOs are too rich or
when a simpler shape is needed for handler I/O.

All command ``Result`` types are colocated here so that handlers stay
focused on transitions / orchestration and consumers have a single
import path for return shapes.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime

from src.modules.logistics.domain.value_objects import (
    DeliveryQuote,
)

# ---------------------------------------------------------------------------
# Query results
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Command results
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CreateShipmentResult:
    """Output of ``CreateShipmentHandler``.

    Attributes:
        shipment_id: UUID of the newly created shipment (DRAFT status).
    """

    shipment_id: uuid.UUID


@dataclass(frozen=True)
class BookShipmentResult:
    """Output of ``BookShipmentHandler``.

    Attributes:
        shipment_id: UUID of the booked shipment.
        provider_shipment_id: Provider's shipment identifier.
        tracking_number: Provider's tracking number (may be ``None``).
    """

    shipment_id: uuid.UUID
    provider_shipment_id: str
    tracking_number: str | None


@dataclass(frozen=True)
class CancelShipmentResult:
    """Output of ``CancelShipmentHandler``.

    Attributes:
        shipment_id: UUID of the cancelled shipment.
    """

    shipment_id: uuid.UUID


@dataclass(frozen=True)
class IngestTrackingResult:
    """Output of ``IngestTrackingHandler``.

    Attributes:
        shipment_id: UUID of the updated shipment.
        new_events_count: Number of genuinely new events (after dedup).
    """

    shipment_id: uuid.UUID
    new_events_count: int
