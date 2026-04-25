"""Unit tests for the Shipment aggregate root — FSM transitions, factory, tracking events."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from src.modules.logistics.domain.entities import Shipment
from src.modules.logistics.domain.events import (
    ShipmentBookedEvent,
    ShipmentBookingFailedEvent,
    ShipmentBookingRequestedEvent,
    ShipmentCancellationFailedEvent,
    ShipmentCancellationRequestedEvent,
    ShipmentCancelledEvent,
    ShipmentCreatedEvent,
    ShipmentEditTaskCompletedEvent,
    ShipmentEditTaskFailedEvent,
    ShipmentEditTaskScheduledEvent,
    ShipmentTrackingUpdatedEvent,
)
from src.modules.logistics.domain.exceptions import InvalidShipmentTransitionError
from src.modules.logistics.domain.value_objects import (
    PROVIDER_CDEK,
    Address,
    CashOnDelivery,
    ContactInfo,
    DeliveryQuote,
    DeliveryType,
    Dimensions,
    EditTaskKind,
    EditTaskStatus,
    EstimatedDelivery,
    Money,
    Parcel,
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
        "region": "Московская область",
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
    return Address(**defaults)  # ty:ignore[invalid-argument-type]


def _make_contact(**overrides) -> ContactInfo:
    defaults = {
        "first_name": "Иван",
        "last_name": "Иванов",
        "phone": "+79001234567",
        "middle_name": "Петрович",
        "email": None,
    }
    defaults.update(overrides)
    return ContactInfo(**defaults)


def _make_quote(**overrides) -> DeliveryQuote:
    defaults = {
        "id": uuid.uuid4(),
        "rate": ShippingRate(
            provider_code=PROVIDER_CDEK,
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
    sender = overrides.pop("sender", _make_contact())
    recipient = overrides.pop(
        "recipient",
        _make_contact(first_name="Пётр", last_name="Петров", middle_name=None),
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
        sender=sender,
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
        assert shipment.provider_code == PROVIDER_CDEK
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

    def test_create_stores_sender(self):
        sender = _make_contact(first_name="Олег", last_name="Олегов")
        shipment = _make_shipment(sender=sender)
        assert shipment.sender == sender
        assert shipment.sender.full_name == "Олегов Олег Петрович"

    def test_create_with_cod(self):
        cod = CashOnDelivery(
            amount=Money(amount=500000, currency_code="RUB"),
            payment_method="cash",
        )
        shipment = _make_shipment(cod=cod)
        assert shipment.cod == cod


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

    def test_booking_pending_to_booked_with_estimated_delivery(self):
        shipment = _make_shipment()
        shipment.mark_booking_pending()
        ed = EstimatedDelivery(min_days=3, max_days=5)
        shipment.mark_booked(
            provider_shipment_id="X",
            tracking_number="Y",
            estimated_delivery=ed,
        )
        assert shipment.estimated_delivery == ed

    def test_booking_pending_to_failed(self):
        shipment = _make_shipment()
        shipment.mark_booking_pending()
        shipment.clear_domain_events()
        shipment.mark_booking_failed(reason="provider rejected")
        assert shipment.status == ShipmentStatus.FAILED
        assert shipment.failure_reason == "provider rejected"
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

    def test_cancel_pending_reverts_to_booked_on_failure(self):
        """When provider rejects cancellation the shipment is still with carrier."""
        shipment = _make_shipment()
        shipment.mark_booking_pending()
        shipment.mark_booked(provider_shipment_id="X", tracking_number="Y")
        shipment.mark_cancel_pending()
        shipment.clear_domain_events()
        shipment.mark_cancellation_failed(reason="already shipped")
        assert shipment.status == ShipmentStatus.BOOKED
        assert shipment.failure_reason == "already shipped"
        events = shipment.domain_events
        assert any(isinstance(e, ShipmentCancellationFailedEvent) for e in events)

    def test_draft_can_be_cancelled_directly(self):
        """DRAFT → CANCELLED is allowed (user cancels before booking)."""
        shipment = _make_shipment()
        shipment.cancel_draft()
        assert shipment.status == ShipmentStatus.CANCELLED

    def test_version_increments_on_transition(self):
        """Each FSM transition must bump the optimistic lock version."""
        shipment = _make_shipment()
        initial_version = shipment.version
        shipment.mark_booking_pending()
        assert shipment.version == initial_version + 1
        shipment.mark_booked(provider_shipment_id="X", tracking_number="Y")
        assert shipment.version == initial_version + 2

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

    def test_out_of_order_events_do_not_regress_latest_status(self):
        """When an older event arrives late, latest_tracking_status stays correct."""
        shipment = self._booked_shipment()
        now = datetime.now(UTC)
        # First: a later event arrives
        e_later = TrackingEvent(
            status=TrackingStatus.IN_TRANSIT,
            provider_status_code="T",
            provider_status_name="Transit",
            timestamp=now + timedelta(hours=2),
            location=None,
            description=None,
        )
        shipment.append_tracking_event(e_later)
        assert shipment.latest_tracking_status == TrackingStatus.IN_TRANSIT

        # Then: an earlier event arrives late
        e_earlier = TrackingEvent(
            status=TrackingStatus.ACCEPTED,
            provider_status_code="A",
            provider_status_name="Accepted",
            timestamp=now,
            location=None,
            description=None,
        )
        shipment.append_tracking_event(e_earlier)
        # Latest must NOT regress to ACCEPTED
        assert shipment.latest_tracking_status == TrackingStatus.IN_TRANSIT
        assert len(shipment.tracking_events) == 2

    def test_tracking_event_increments_version(self):
        shipment = self._booked_shipment()
        v_before = shipment.version
        event = TrackingEvent(
            status=TrackingStatus.ACCEPTED,
            provider_status_code="A",
            provider_status_name="Accepted",
            timestamp=datetime.now(UTC),
            location=None,
            description=None,
        )
        shipment.append_tracking_event(event)
        assert shipment.version == v_before + 1


# ---------------------------------------------------------------------------
# Edit-task lifecycle
# ---------------------------------------------------------------------------


class TestEditTaskLifecycle:
    def _booked_shipment(self) -> Shipment:
        s = _make_shipment()
        s.mark_booking_pending()
        s.mark_booked(provider_shipment_id="X", tracking_number="Y")
        s.clear_domain_events()
        return s

    def test_record_edit_task_emits_scheduled_event(self):
        shipment = self._booked_shipment()
        shipment.record_edit_task("task-1", EditTaskKind.EDIT_ORDER)

        assert len(shipment.pending_edit_tasks) == 1
        assert shipment.pending_edit_tasks[0].task_id == "task-1"
        assert any(
            isinstance(e, ShipmentEditTaskScheduledEvent)
            for e in shipment.domain_events
        )

    def test_record_replaces_same_kind(self):
        shipment = self._booked_shipment()
        shipment.record_edit_task("task-1", EditTaskKind.EDIT_PACKAGES)
        shipment.record_edit_task("task-2", EditTaskKind.EDIT_PACKAGES)

        assert len(shipment.pending_edit_tasks) == 1
        assert shipment.pending_edit_tasks[0].task_id == "task-2"

    def test_settle_success_emits_completed_event(self):
        shipment = self._booked_shipment()
        shipment.record_edit_task("task-1", EditTaskKind.EDIT_ORDER)
        shipment.clear_domain_events()

        shipment.settle_edit_task("task-1", EditTaskStatus.SUCCESS)

        assert shipment.pending_edit_tasks == []
        events = shipment.domain_events
        assert any(isinstance(e, ShipmentEditTaskCompletedEvent) for e in events)
        assert not any(isinstance(e, ShipmentEditTaskFailedEvent) for e in events)

    def test_settle_failure_emits_failed_event_with_reason(self):
        shipment = self._booked_shipment()
        shipment.record_edit_task("task-1", EditTaskKind.REMOVE_ITEMS)
        shipment.clear_domain_events()

        shipment.settle_edit_task(
            "task-1", EditTaskStatus.FAILURE, reason="provider rejected"
        )

        failed = next(
            e
            for e in shipment.domain_events
            if isinstance(e, ShipmentEditTaskFailedEvent)
        )
        assert failed.reason == "provider rejected"
        assert failed.kind == EditTaskKind.REMOVE_ITEMS.value

    def test_settle_unknown_task_id_is_noop(self):
        shipment = self._booked_shipment()
        shipment.record_edit_task("task-1", EditTaskKind.EDIT_ORDER)
        v_before = shipment.version
        shipment.clear_domain_events()

        shipment.settle_edit_task("does-not-exist", EditTaskStatus.SUCCESS)

        assert len(shipment.pending_edit_tasks) == 1
        assert shipment.version == v_before
        assert shipment.domain_events == []

    def test_settle_rejects_non_terminal_status(self):
        shipment = self._booked_shipment()
        shipment.record_edit_task("task-1", EditTaskKind.EDIT_ORDER)

        with pytest.raises(ValueError):
            shipment.settle_edit_task("task-1", EditTaskStatus.PENDING)


# ---------------------------------------------------------------------------
# ContactInfo value object
# ---------------------------------------------------------------------------


class TestContactInfo:
    def test_full_name_with_middle_name(self):
        c = ContactInfo(
            first_name="Иван",
            last_name="Иванов",
            phone="+79001234567",
            middle_name="Петрович",
        )
        assert c.full_name == "Иванов Иван Петрович"

    def test_full_name_without_middle_name(self):
        c = ContactInfo(first_name="Иван", last_name="Иванов", phone="+79001234567")
        assert c.full_name == "Иванов Иван"
