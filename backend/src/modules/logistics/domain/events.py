"""
Logistics domain events.

Events are plain (non-frozen) dataclasses — DomainEvent base is non-frozen.
Treat all fields as immutable after construction.
Part of the domain layer — zero framework imports.
"""

import uuid
from dataclasses import dataclass
from typing import ClassVar

from src.shared.interfaces.entities import DomainEvent

# ---------------------------------------------------------------------------
# Intermediate base for logistics events
# ---------------------------------------------------------------------------


@dataclass
class LogisticsEvent(DomainEvent):
    """Base class for all logistics domain events.

    Concrete subclasses supply ``_required_fields`` and
    ``_aggregate_id_field`` via ``__init_subclass__`` keyword arguments,
    following the same pattern as ``CatalogEvent``.
    """

    _required_fields: ClassVar[tuple[str, ...]] = ()
    _aggregate_id_field: ClassVar[str] = ""

    aggregate_type: str = "Logistics"
    event_type: str = "LogisticsEvent"

    def __init_subclass__(
        cls,
        *,
        required_fields: tuple[str, ...] | None = None,
        aggregate_id_field: str | None = None,
        **kwargs: object,
    ) -> None:
        super().__init_subclass__(**kwargs)
        if required_fields is not None:
            cls._required_fields = required_fields
        if aggregate_id_field is not None:
            cls._aggregate_id_field = aggregate_id_field

        if required_fields is not None:
            if cls.event_type == "LogisticsEvent":
                raise TypeError(
                    f"{cls.__name__} must define its own 'event_type' "
                    f"(inherited default 'LogisticsEvent' would misroute events)"
                )
            if cls.aggregate_type == "Logistics":
                raise TypeError(
                    f"{cls.__name__} must define its own 'aggregate_type' "
                    f"(inherited default 'Logistics' would misroute events)"
                )

    def __post_init__(self) -> None:
        cls_name = type(self).__name__
        for field_name in self._required_fields:
            if getattr(self, field_name) is None:
                raise ValueError(f"{field_name} is required for {cls_name}")
        if not self.aggregate_id and self._aggregate_id_field:
            self.aggregate_id = str(getattr(self, self._aggregate_id_field))


# ---------------------------------------------------------------------------
# Shipment lifecycle events
# ---------------------------------------------------------------------------


@dataclass
class ShipmentCreatedEvent(
    LogisticsEvent,
    required_fields=("shipment_id",),
    aggregate_id_field="shipment_id",
):
    """Emitted when a new Shipment is created in DRAFT status."""

    shipment_id: uuid.UUID | None = None
    provider_code: str = ""
    service_code: str = ""
    aggregate_type: str = "Shipment"
    event_type: str = "ShipmentCreatedEvent"


@dataclass
class ShipmentBookingRequestedEvent(
    LogisticsEvent,
    required_fields=("shipment_id",),
    aggregate_id_field="shipment_id",
):
    """Emitted when shipment transitions DRAFT → BOOKING_PENDING."""

    shipment_id: uuid.UUID | None = None
    aggregate_type: str = "Shipment"
    event_type: str = "ShipmentBookingRequestedEvent"


@dataclass
class ShipmentBookedEvent(
    LogisticsEvent,
    required_fields=("shipment_id",),
    aggregate_id_field="shipment_id",
):
    """Emitted when provider confirms the booking (BOOKING_PENDING → BOOKED).

    ``tracking_number`` is ``None`` when the provider has not yet assigned one
    (e.g. CDEK ИМ-orders before parcel handover). Downstream consumers must
    distinguish absence from an empty string.
    """

    shipment_id: uuid.UUID | None = None
    provider_shipment_id: str = ""
    tracking_number: str | None = None
    aggregate_type: str = "Shipment"
    event_type: str = "ShipmentBookedEvent"


@dataclass
class ShipmentBookingFailedEvent(
    LogisticsEvent,
    required_fields=("shipment_id",),
    aggregate_id_field="shipment_id",
):
    """Emitted when provider rejects the booking (BOOKING_PENDING → FAILED)."""

    shipment_id: uuid.UUID | None = None
    reason: str = ""
    aggregate_type: str = "Shipment"
    event_type: str = "ShipmentBookingFailedEvent"


@dataclass
class ShipmentCancellationRequestedEvent(
    LogisticsEvent,
    required_fields=("shipment_id",),
    aggregate_id_field="shipment_id",
):
    """Emitted when cancellation is initiated (BOOKED → CANCEL_PENDING)."""

    shipment_id: uuid.UUID | None = None
    aggregate_type: str = "Shipment"
    event_type: str = "ShipmentCancellationRequestedEvent"


@dataclass
class ShipmentCancelledEvent(
    LogisticsEvent,
    required_fields=("shipment_id",),
    aggregate_id_field="shipment_id",
):
    """Emitted when provider confirms cancellation (CANCEL_PENDING → CANCELLED)."""

    shipment_id: uuid.UUID | None = None
    aggregate_type: str = "Shipment"
    event_type: str = "ShipmentCancelledEvent"


@dataclass
class ShipmentCancellationFailedEvent(
    LogisticsEvent,
    required_fields=("shipment_id",),
    aggregate_id_field="shipment_id",
):
    """Emitted when provider rejects cancellation (CANCEL_PENDING → BOOKED)."""

    shipment_id: uuid.UUID | None = None
    reason: str = ""
    aggregate_type: str = "Shipment"
    event_type: str = "ShipmentCancellationFailedEvent"


@dataclass
class ShipmentTrackingUpdatedEvent(
    LogisticsEvent,
    required_fields=("shipment_id",),
    aggregate_id_field="shipment_id",
):
    """Emitted when new tracking events are ingested (webhook or poll)."""

    shipment_id: uuid.UUID | None = None
    new_status: str = ""
    provider_status_code: str = ""
    aggregate_type: str = "Shipment"
    event_type: str = "ShipmentTrackingUpdatedEvent"


# ---------------------------------------------------------------------------
# Edit / mutation events (Yandex 3.06 / 3.12 / 3.14 / 3.15)
# ---------------------------------------------------------------------------


@dataclass
class ShipmentRecipientUpdatedEvent(
    LogisticsEvent,
    required_fields=("shipment_id",),
    aggregate_id_field="shipment_id",
):
    """Emitted after a successful recipient mutation via /request/edit."""

    shipment_id: uuid.UUID | None = None
    aggregate_type: str = "Shipment"
    event_type: str = "ShipmentRecipientUpdatedEvent"


@dataclass
class ShipmentDestinationUpdatedEvent(
    LogisticsEvent,
    required_fields=("shipment_id",),
    aggregate_id_field="shipment_id",
):
    """Emitted after a successful destination mutation via /request/edit."""

    shipment_id: uuid.UUID | None = None
    aggregate_type: str = "Shipment"
    event_type: str = "ShipmentDestinationUpdatedEvent"


@dataclass
class ShipmentEditTaskScheduledEvent(
    LogisticsEvent,
    required_fields=("shipment_id", "task_id", "kind"),
    aggregate_id_field="shipment_id",
):
    """Emitted when an asynchronous edit task is submitted to the provider.

    ``kind`` mirrors :class:`EditTaskKind` so consumers can route by
    operation (places / items / removal / recipient / destination)
    without coupling to the original command class.
    """

    shipment_id: uuid.UUID | None = None
    task_id: str | None = None
    kind: str | None = None  # value of EditTaskKind
    aggregate_type: str = "Shipment"
    event_type: str = "ShipmentEditTaskScheduledEvent"


# ---------------------------------------------------------------------------
# Intake events (CDEK courier pickup)
# ---------------------------------------------------------------------------


@dataclass
class ShipmentIntakeScheduledEvent(
    LogisticsEvent,
    required_fields=("shipment_id", "provider_intake_id"),
    aggregate_id_field="shipment_id",
):
    """Emitted when a courier intake is registered with the provider."""

    shipment_id: uuid.UUID | None = None
    provider_intake_id: str | None = None
    intake_status: str = ""  # IntakeStatus value
    aggregate_type: str = "Shipment"
    event_type: str = "ShipmentIntakeScheduledEvent"


@dataclass
class ShipmentIntakeCancelledEvent(
    LogisticsEvent,
    required_fields=("provider_intake_id",),
    aggregate_id_field="provider_intake_id",
):
    """Emitted when a courier intake is cancelled.

    Aggregate id is the provider intake id rather than shipment id —
    intake-cancel commands operate without a Shipment aggregate
    (CancelIntakeCommand only carries provider_code + provider_intake_id).
    """

    provider_intake_id: str | None = None
    aggregate_type: str = "Intake"
    event_type: str = "ShipmentIntakeCancelledEvent"


# ---------------------------------------------------------------------------
# Return / refusal events (CDEK reverse flow)
# ---------------------------------------------------------------------------


@dataclass
class ShipmentReturnRegisteredEvent(
    LogisticsEvent,
    required_fields=("shipment_id",),
    aggregate_id_field="shipment_id",
):
    """Emitted when a client return is registered with the provider."""

    shipment_id: uuid.UUID | None = None
    provider_return_id: str | None = None
    aggregate_type: str = "Shipment"
    event_type: str = "ShipmentReturnRegisteredEvent"


@dataclass
class ShipmentRefusalRegisteredEvent(
    LogisticsEvent,
    required_fields=("shipment_id",),
    aggregate_id_field="shipment_id",
):
    """Emitted when a doorstep refusal is registered with the provider."""

    shipment_id: uuid.UUID | None = None
    reason: str | None = None
    aggregate_type: str = "Shipment"
    event_type: str = "ShipmentRefusalRegisteredEvent"
