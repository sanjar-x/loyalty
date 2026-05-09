"""Read models for logistics CQRS queries.

Frozen dataclasses returned by query handlers that read directly from
the ``shipments`` table (CQRS read-side exemption — see
``tests/architecture/test_boundaries.py`` Rule 3). Schemas in
``presentation`` map these to Pydantic models for the wire.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class AdminShipmentSummary:
    """Compact list-view projection of a shipment for the admin dashboard.

    Carries just enough to populate the table row without re-issuing the
    full ``GET /shipments/{id}`` request. ``destination_city`` is
    extracted from ``destination_json["city"]`` so the list does not
    need to surface the full address payload.

    Attributes:
        id: Shipment UUID.
        provider_code: Open provider identifier (``cdek`` /
            ``yandex_delivery`` / ``dobropost`` / ...).
        status: Local FSM state (``draft`` / ``booked`` / ...).
        tracking_number: Carrier-assigned tracking number, ``None`` if
            booking has not landed.
        order_id: Linked order UUID, ``None`` for ad-hoc shipments.
        delivery_type: ``courier`` / ``pickup_point`` / ``post_office``.
        destination_city: Recipient city for the row preview.
        quoted_cost_amount: Quoted cost in the smallest currency unit.
        quoted_cost_currency: ISO 4217 code.
        latest_tracking_status: Denormalised carrier status for quick
            row-level rendering, ``None`` until the first tracking event.
        created_at: Record creation timestamp.
        updated_at: Last modification timestamp.
        booked_at: Provider booking confirmation timestamp.
    """

    id: uuid.UUID
    provider_code: str
    status: str
    tracking_number: str | None
    order_id: uuid.UUID | None
    delivery_type: str
    destination_city: str
    quoted_cost_amount: int
    quoted_cost_currency: str
    latest_tracking_status: str | None
    created_at: datetime
    updated_at: datetime
    booked_at: datetime | None


@dataclass(frozen=True)
class AdminShipmentListPage:
    """Cursor-paginated page of :class:`AdminShipmentSummary` rows.

    Attributes:
        items: Ordered by ``created_at DESC`` (then ``id DESC`` for
            ties).
        next_cursor: ``created_at`` of the last item, or ``None`` when
            the result fits entirely in ``items`` (no more pages).
    """

    items: list[AdminShipmentSummary]
    next_cursor: datetime | None
