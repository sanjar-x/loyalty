"""Unit tests for the Shipment aggregate root — FSM transitions, factory, tracking events."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from src.modules.logistics.domain.entities import Shipment
from src.modules.logistics.domain.events import (
    ShipmentBookedEvent,
    ShipmentBookingFailedEvent,
    ShipmentBookingRequestedEvent,
    ShipmentCancellationRequestedEvent,
    ShipmentCancelledEvent,
    ShipmentCreatedEvent,
    ShipmentTrackingUpdatedEvent,
)
from src.modules.logistics.domain.exceptions import InvalidShipmentTransitionError
from src.modules.logistics.domain.value_objects import (
    Address,
    ContactInfo,
    DeliveryQuote,
    DeliveryType,
    Dimensions,
    Money,
    Parcel,
    ProviderCode,
    ShipmentStatus,
    ShippingRate,
    TrackingEvent,
    TrackingStatus,
    Weight,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_address(**overrides) -> Address:
    defaults = {
        "country_code": "RU",
        "city": "Москва",
        "postal_code": "101000",
        "street": "Тверская",
        "house": "1",
        "apartment": None,
        "subdivision_code": None,
        "latitude": 55.756,
        "longitude": 37.617,
        "raw_address": None,
    }
    defaults.update(overrides)
    return Address(**defaults)


def _make_quote(**overrides) -> DeliveryQuote:
    defaults = {
        "id": uuid.uuid4(),
        "rate": ShippingRate(
            provider_code=ProviderCode.CDEK,
            service_code="136",
            service_name="Посылка склад-склад",
            delivery_type=DeliveryType.PICKUP_POINT,
            total_cost=Money(amount=35000, currency_code="RUB"),
            base_cost=Money(amount=30000, currency_code="RUB"),
            insurance_cost=Money(amount=5000, currency_code="RUB"),
            delivery_days_min=3,
            delivery_days_max=5,
        ),
        "provider_payload": '{"offer_id": "abc123"}',
        "quoted_at": datetime.now(UTC),
        "expires_at": datetime.now(UTC) + timedelta(hours=1),
    }
    defaults.update(overrides)
    return DeliveryQuote(**defaults)


def _make_shipment(**overrides) -> Shipment:
    """Create a DRAFT shipment using factory method."""
    quote = overrides.pop("quote", _make_quote())
    origin = overrides.pop("origin", _make_address())
    destination = overrides.pop("destination", _make_address(city="Казань"))
    recipient = overrides.pop(
        "recipient",
        ContactInfo(full_name="Иван Иванов", phone="+79001234567", email=None),
    )
    parcels = overrides.pop(
        "parcels",
        [
            Parcel(
                weight=Weight(grams=1000),
                dimensions=Dimensions(length_cm=30, width_cm=20, height_cm=15),
                declared_value=Money(amount=500000, currency_code="RUB"),
                description="Товар",
            )
        ],
    )
    return Shipment.create(
        quote=quote,
        origin=origin,
        destination=destination,
        recipient=recipient,
        parcels=parcels,
        **overrides,
    )


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------


class TestShipmentCreate:
    def test_create_sets_draft_status(self):
        shipment = _make_shipment()
        assert shipment.status == ShipmentStatus.DRAFT

    def test_create_assigns_uuid(self):
        shipment = _make_shipment()
        assert isinstance(shipment.id, uuid.UUID)

    def test_create_captures_quote_data(self):
        quote = _make_quote()
        shipment = _make_shipment(quote=quote)
        assert shipment.provider_code == ProviderCode.CDEK
        assert shipment.service_code == "136"
        assert shipment.delivery_type == DeliveryType.PICKUP_POINT
        assert shipment.quoted_cost == quote.rate.total_cost
        assert shipment.provider_payload == quote.provider_payload

    def test_create_emits_created_event(self):
        shipment = _make_shipment()
        events = shipment.domain_events
        assert len(events) == 1
        assert isinstance(events[0], ShipmentCreatedEvent)

    def test_create_with_order_id(self):
        oid = uuid.uuid4()
        shipment = _make_shipment(order_id=oid)
        assert shipment.order_id == oid

    def test_create_with_explicit_shipment_id(self):
        sid = uuid.uuid4()
        shipment = _make_shipment(shipment_id=sid)
        assert shipment.id == sid


# ---------------------------------------------------------------------------
# FSM transitions
# ---------------------------------------------------------------------------


class TestShipmentFSM:
    def test_draft_to_booking_pending(self):
        shipment = _make_shipment()
        shipment.clear_domain_events()
        shipment.mark_booking_pending()
        assert shipment.status == ShipmentStatus.BOOKING_PENDING
        events = shipment.domain_events
        assert any(isinstance(e, ShipmentBookingRequestedEvent) for e in events)

    def test_booking_pending_to_booked(self):
        shipment = _make_shipment()
        shipment.mark_booking_pending()
        shipment.clear_domain_events()
        shipment.mark_booked(provider_shipment_id="CDK-12345", tracking_number="TN-99")
        assert shipment.status == ShipmentStatus.BOOKED
        assert shipment.provider_shipment_id == "CDK-12345"
        assert shipment.tracking_number == "TN-99"
        assert shipment.booked_at is not None
        events = shipment.domain_events
        assert any(isinstance(e, ShipmentBookedEvent) for e in events)

    def test_booking_pending_to_failed(self):
        shipment = _make_shipment()
        shipment.mark_booking_pending()
        shipment.clear_domain_events()
        shipment.mark_booking_failed(reason="provider rejected")
        assert shipment.status == ShipmentStatus.FAILED
        events = shipment.domain_events
        assert any(isinstance(e, ShipmentBookingFailedEvent) for e in events)

    def test_booked_to_cancel_pending(self):
        shipment = _make_shipment()
        shipment.mark_booking_pending()
        shipment.mark_booked(provider_shipment_id="X", tracking_number="Y")
        shipment.clear_domain_events()
        shipment.mark_cancel_pending()
        assert shipment.status == ShipmentStatus.CANCEL_PENDING
        events = shipment.domain_events
        assert any(isinstance(e, ShipmentCancellationRequestedEvent) for e in events)

    def test_cancel_pending_to_cancelled(self):
        shipment = _make_shipment()
        shipment.mark_booking_pending()
        shipment.mark_booked(provider_shipment_id="X", tracking_number="Y")
        shipment.mark_cancel_pending()
        shipment.clear_domain_events()
        shipment.mark_cancelled()
        assert shipment.status == ShipmentStatus.CANCELLED
        assert shipment.cancelled_at is not None
        events = shipment.domain_events
        assert any(isinstance(e, ShipmentCancelledEvent) for e in events)

    def test_cancel_pending_to_failed(self):
        shipment = _make_shipment()
        shipment.mark_booking_pending()
        shipment.mark_booked(provider_shipment_id="X", tracking_number="Y")
        shipment.mark_cancel_pending()
        shipment.mark_cancellation_failed(reason="already shipped")
        assert shipment.status == ShipmentStatus.FAILED

    def test_draft_can_be_cancelled_directly(self):
        """DRAFT → CANCELLED is allowed (user cancels before booking)."""
        shipment = _make_shipment()
        shipment.mark_cancelled()
        assert shipment.status == ShipmentStatus.CANCELLED

    # Invalid transitions
    def test_draft_to_booked_raises(self):
        shipment = _make_shipment()
        with pytest.raises(InvalidShipmentTransitionError):
            shipment.mark_booked(provider_shipment_id="X", tracking_number="Y")

    def test_booked_to_booking_pending_raises(self):
        shipment = _make_shipment()
        shipment.mark_booking_pending()
        shipment.mark_booked(provider_shipment_id="X", tracking_number="Y")
        with pytest.raises(InvalidShipmentTransitionError):
            shipment.mark_booking_pending()

    def test_failed_is_terminal(self):
        shipment = _make_shipment()
        shipment.mark_booking_pending()
        shipment.mark_booking_failed(reason="oops")
        with pytest.raises(InvalidShipmentTransitionError):
            shipment.mark_booking_pending()

    def test_cancelled_is_terminal(self):
        shipment = _make_shipment()
        shipment.mark_booking_pending()
        shipment.mark_booked(provider_shipment_id="X", tracking_number="Y")
        shipment.mark_cancel_pending()
        shipment.mark_cancelled()
        with pytest.raises(InvalidShipmentTransitionError):
            shipment.mark_booking_pending()


# ---------------------------------------------------------------------------
# Tracking events
# ---------------------------------------------------------------------------


class TestShipmentTracking:
    def _booked_shipment(self) -> Shipment:
        s = _make_shipment()
        s.mark_booking_pending()
        s.mark_booked(provider_shipment_id="X", tracking_number="Y")
        s.clear_domain_events()
        return s

    def test_append_tracking_event(self):
        shipment = self._booked_shipment()
        event = TrackingEvent(
            status=TrackingStatus.ACCEPTED,
            provider_status_code="ACCEPTED",
            provider_status_name="Принят",
            timestamp=datetime.now(UTC),
            location="Москва",
            description="Принят на склад",
        )
        shipment.append_tracking_event(event)
        assert len(shipment.tracking_events) == 1
        assert shipment.latest_tracking_status == TrackingStatus.ACCEPTED
        events = shipment.domain_events
        assert any(isinstance(e, ShipmentTrackingUpdatedEvent) for e in events)

    def test_deduplication_by_timestamp_and_status(self):
        shipment = self._booked_shipment()
        ts = datetime.now(UTC)
        event = TrackingEvent(
            status=TrackingStatus.IN_TRANSIT,
            provider_status_code="IN_TRANSIT",
            provider_status_name="В пути",
            timestamp=ts,
            location=None,
            description=None,
        )
        shipment.append_tracking_event(event)
        # Same timestamp + status → should be deduplicated
        shipment.append_tracking_event(event)
        assert len(shipment.tracking_events) == 1

    def test_multiple_different_events(self):
        shipment = self._booked_shipment()
        now = datetime.now(UTC)
        e1 = TrackingEvent(
            status=TrackingStatus.ACCEPTED,
            provider_status_code="A",
            provider_status_name="Accepted",
            timestamp=now,
            location=None,
            description=None,
        )
        e2 = TrackingEvent(
            status=TrackingStatus.IN_TRANSIT,
            provider_status_code="T",
            provider_status_name="Transit",
            timestamp=now + timedelta(hours=1),
            location=None,
            description=None,
        )
        shipment.append_tracking_event(e1)
        shipment.append_tracking_event(e2)
        assert len(shipment.tracking_events) == 2
        assert shipment.latest_tracking_status == TrackingStatus.IN_TRANSIT
