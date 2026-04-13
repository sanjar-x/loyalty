"""
Shipment aggregate root — central logistics domain entity.

Owns the **local integration lifecycle** (DRAFT → BOOKED → CANCELLED / FAILED).
Carrier lifecycle is tracked as append-only TrackingEvents.
Part of the domain layer — zero infrastructure imports.
"""

import uuid
from datetime import UTC, datetime

import attrs

from src.modules.logistics.domain.events import (
    ShipmentBookedEvent,
    ShipmentBookingFailedEvent,
    ShipmentBookingRequestedEvent,
    ShipmentCancellationFailedEvent,
    ShipmentCancellationRequestedEvent,
    ShipmentCancelledEvent,
    ShipmentCreatedEvent,
    ShipmentTrackingUpdatedEvent,
)
from src.modules.logistics.domain.exceptions import InvalidShipmentTransitionError
from src.modules.logistics.domain.value_objects import (
    Address,
    CashOnDelivery,
    ContactInfo,
    DeliveryQuote,
    DeliveryType,
    EstimatedDelivery,
    Money,
    Parcel,
    ProviderCode,
    ShipmentStatus,
    TrackingEvent,
    TrackingStatus,
)
from src.shared.interfaces.entities import AggregateRoot

# ---------------------------------------------------------------------------
# FSM transition table
# ---------------------------------------------------------------------------

_ALLOWED_TRANSITIONS: dict[ShipmentStatus, frozenset[ShipmentStatus]] = {
    ShipmentStatus.DRAFT: frozenset(
        {
            ShipmentStatus.BOOKING_PENDING,
            ShipmentStatus.CANCELLED,
        }
    ),
    ShipmentStatus.BOOKING_PENDING: frozenset(
        {
            ShipmentStatus.BOOKED,
            ShipmentStatus.FAILED,
        }
    ),
    ShipmentStatus.BOOKED: frozenset({ShipmentStatus.CANCEL_PENDING}),
    ShipmentStatus.CANCEL_PENDING: frozenset(
        {
            ShipmentStatus.CANCELLED,
            ShipmentStatus.BOOKED,  # revert when provider rejects cancellation
        }
    ),
    ShipmentStatus.CANCELLED: frozenset(),
    ShipmentStatus.FAILED: frozenset(),
}


@attrs.define
class Shipment(AggregateRoot):
    """Shipment aggregate root.

    Tracks the local integration workflow. Provider-specific carrier
    lifecycle is represented as append-only ``tracking_events``.

    Attributes:
        id: Unique shipment identifier.
        order_id: Optional link to the order / checkout that triggered this shipment.
        provider_code: Which logistics provider handles this shipment.
        service_code: Provider-specific tariff / service code selected at quote time.
        delivery_type: Courier, pickup point, or post office.
        status: Local FSM state (see ``ShipmentStatus``).
        origin: Sender address.
        destination: Recipient address.
        recipient: Recipient contact details.
        parcels: One or more packages in this shipment.
        quoted_cost: Cost at the time of quote selection.
        provider_shipment_id: Assigned by the provider after booking.
        tracking_number: Assigned by the provider after booking.
        provider_payload: Opaque JSON from the DeliveryQuote, used during booking.
        tracking_events: Append-only carrier event history.
        latest_tracking_status: Denormalized latest carrier status for queries.
        created_at: When the shipment record was created.
        updated_at: Last modification timestamp.
        booked_at: When the provider confirmed the booking.
        cancelled_at: When cancellation was confirmed.
        version: Optimistic locking counter.
    """

    id: uuid.UUID
    order_id: uuid.UUID | None
    provider_code: ProviderCode
    service_code: str
    delivery_type: DeliveryType
    status: ShipmentStatus

    origin: Address
    destination: Address
    sender: ContactInfo
    recipient: ContactInfo
    parcels: list[Parcel]

    quoted_cost: Money
    cod: CashOnDelivery | None = None

    provider_shipment_id: str | None = None
    tracking_number: str | None = None
    provider_payload: str | None = None

    tracking_events: list[TrackingEvent] = attrs.Factory(list)
    latest_tracking_status: TrackingStatus | None = None

    failure_reason: str | None = None
    estimated_delivery: EstimatedDelivery | None = None

    created_at: datetime = attrs.Factory(lambda: datetime.now(UTC))
    updated_at: datetime = attrs.Factory(lambda: datetime.now(UTC))
    booked_at: datetime | None = None
    cancelled_at: datetime | None = None

    version: int = 1

    # -- Factory method -----------------------------------------------------

    @classmethod
    def create(
        cls,
        *,
        quote: DeliveryQuote,
        origin: Address,
        destination: Address,
        sender: ContactInfo,
        recipient: ContactInfo,
        parcels: list[Parcel],
        order_id: uuid.UUID | None = None,
        shipment_id: uuid.UUID | None = None,
        cod: CashOnDelivery | None = None,
    ) -> Shipment:
        """Create a new shipment in DRAFT status from a selected DeliveryQuote."""
        now = datetime.now(UTC)
        shipment = cls(
            id=shipment_id or uuid.uuid4(),
            order_id=order_id,
            provider_code=quote.rate.provider_code,
            service_code=quote.rate.service_code,
            delivery_type=quote.rate.delivery_type,
            status=ShipmentStatus.DRAFT,
            origin=origin,
            destination=destination,
            sender=sender,
            recipient=recipient,
            parcels=list(parcels),
            quoted_cost=quote.rate.total_cost,
            cod=cod,
            provider_payload=quote.provider_payload,
            tracking_events=[],
            created_at=now,
            updated_at=now,
        )
        shipment.add_domain_event(
            ShipmentCreatedEvent(
                shipment_id=shipment.id,
                provider_code=quote.rate.provider_code,
                service_code=quote.rate.service_code,
            )
        )
        return shipment

    # -- FSM transitions ----------------------------------------------------

    def _transition_to(self, target: ShipmentStatus) -> None:
        allowed = _ALLOWED_TRANSITIONS.get(self.status, frozenset())
        if target not in allowed:
            raise InvalidShipmentTransitionError(
                current_status=self.status.value,
                target_status=target.value,
            )
        self.status = target
        self.updated_at = datetime.now(UTC)
        self.version += 1

    def mark_booking_pending(self) -> None:
        """Transition DRAFT → BOOKING_PENDING."""
        self._transition_to(ShipmentStatus.BOOKING_PENDING)
        self.add_domain_event(ShipmentBookingRequestedEvent(shipment_id=self.id))

    def mark_booked(
        self,
        provider_shipment_id: str,
        tracking_number: str | None = None,
        estimated_delivery: EstimatedDelivery | None = None,
    ) -> None:
        """Transition BOOKING_PENDING → BOOKED."""
        self._transition_to(ShipmentStatus.BOOKED)
        self.provider_shipment_id = provider_shipment_id
        self.tracking_number = tracking_number
        self.estimated_delivery = estimated_delivery
        self.booked_at = datetime.now(UTC)
        self.add_domain_event(
            ShipmentBookedEvent(
                shipment_id=self.id,
                provider_shipment_id=provider_shipment_id,
                tracking_number=tracking_number or "",
            )
        )

    def mark_booking_failed(self, reason: str) -> None:
        """Transition BOOKING_PENDING → FAILED."""
        self._transition_to(ShipmentStatus.FAILED)
        self.failure_reason = reason
        self.add_domain_event(
            ShipmentBookingFailedEvent(
                shipment_id=self.id,
                reason=reason,
            )
        )

    def mark_cancel_pending(self) -> None:
        """Transition BOOKED → CANCEL_PENDING."""
        self._transition_to(ShipmentStatus.CANCEL_PENDING)
        self.add_domain_event(ShipmentCancellationRequestedEvent(shipment_id=self.id))

    def mark_cancelled(self) -> None:
        """Transition CANCEL_PENDING → CANCELLED."""
        self._transition_to(ShipmentStatus.CANCELLED)
        self.cancelled_at = datetime.now(UTC)
        self.add_domain_event(ShipmentCancelledEvent(shipment_id=self.id))

    def mark_cancellation_failed(self, reason: str) -> None:
        """Transition CANCEL_PENDING → BOOKED (shipment still active with carrier)."""
        self._transition_to(ShipmentStatus.BOOKED)
        self.failure_reason = reason
        self.add_domain_event(
            ShipmentCancellationFailedEvent(
                shipment_id=self.id,
                reason=reason,
            )
        )

    def cancel_draft(self) -> None:
        """Cancel a shipment that is still in DRAFT (no provider call needed)."""
        self._transition_to(ShipmentStatus.CANCELLED)
        self.cancelled_at = datetime.now(UTC)
        self.add_domain_event(ShipmentCancelledEvent(shipment_id=self.id))

    # -- Tracking -----------------------------------------------------------

    def append_tracking_event(self, event: TrackingEvent) -> None:
        """Append a new tracking event from the carrier.

        Deduplicates by (timestamp, status) to ensure idempotency
        when the same event arrives via webhook and polling.

        ``latest_tracking_status`` is always recomputed from the most-recent
        timestamp across *all* events to prevent regression when out-of-order
        events arrive.
        """
        existing_keys = {(e.timestamp, e.status) for e in self.tracking_events}
        if (event.timestamp, event.status) in existing_keys:
            return  # idempotent — already recorded

        self.tracking_events.append(event)

        # Recompute latest from the event with the max timestamp
        latest = max(self.tracking_events, key=lambda e: e.timestamp)
        self.latest_tracking_status = latest.status

        self.updated_at = datetime.now(UTC)
        self.version += 1
        self.add_domain_event(
            ShipmentTrackingUpdatedEvent(
                shipment_id=self.id,
                new_status=event.status.value,
                provider_status_code=event.provider_status_code,
            )
        )
