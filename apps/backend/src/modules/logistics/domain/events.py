"""Logistics domain events.

Logistics spans multiple aggregate kinds (``Shipment``, ``ProviderAccount``,
``CarrierEvent``) within one bounded context, so concrete events MUST
override ``aggregate_type`` with their specific aggregate name. Required-
field validation and ``aggregate_id`` auto-fill come from
:class:`shared.interfaces.entities.ModuleDomainEvent`.
"""

import uuid
from dataclasses import dataclass

from shared.interfaces.entities import ModuleDomainEvent


@dataclass(frozen=True)
class LogisticsEvent(ModuleDomainEvent, abstract=True):
    """Intermediate base for all logistics domain events."""

    aggregate_type: str = "Logistics"

    def __init_subclass__(
        cls,
        *,
        abstract: bool = False,
        required_fields: tuple[str, ...] | None = None,
        aggregate_id_field: str | None = None,
        **kwargs: object,
    ) -> None:
        super().__init_subclass__(
            abstract=abstract,
            required_fields=required_fields,
            aggregate_id_field=aggregate_id_field,
            **kwargs,
        )
        if abstract or required_fields is None:
            return
        if "aggregate_type" not in cls.__dict__:
            raise TypeError(
                f"{cls.__name__} must override 'aggregate_type' — logistics "
                "events span multiple aggregate kinds (Shipment, "
                "ProviderAccount, ...) and cannot inherit the placeholder "
                "'Logistics'."
            )


# ---------------------------------------------------------------------------
# Shipment lifecycle events
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
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


@dataclass(frozen=True)
class ShipmentBookingRequestedEvent(
    LogisticsEvent,
    required_fields=("shipment_id",),
    aggregate_id_field="shipment_id",
):
    """Emitted when shipment transitions DRAFT → BOOKING_PENDING."""

    shipment_id: uuid.UUID | None = None
    aggregate_type: str = "Shipment"
    event_type: str = "ShipmentBookingRequestedEvent"


@dataclass(frozen=True)
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


@dataclass(frozen=True)
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


@dataclass(frozen=True)
class ShipmentDeliveryFailedEvent(
    LogisticsEvent,
    required_fields=("shipment_id",),
    aggregate_id_field="shipment_id",
):
    """Emitted when carrier-side tracking declares the package undeliverable.

    Distinct from :class:`ShipmentBookingFailedEvent` — the booking
    succeeded; the package was lost / refused / damaged in transit.
    Subscribers compensating booking-time failures (release stock,
    refund hold) listen to the booking-failed event only; subscribers
    handling delivery-time failures (issue refund, notify customer)
    listen here.
    """

    shipment_id: uuid.UUID | None = None
    reason: str = ""
    aggregate_type: str = "Shipment"
    event_type: str = "ShipmentDeliveryFailedEvent"


@dataclass(frozen=True)
class ShipmentCancellationRequestedEvent(
    LogisticsEvent,
    required_fields=("shipment_id",),
    aggregate_id_field="shipment_id",
):
    """Emitted when cancellation is initiated (BOOKED → CANCEL_PENDING)."""

    shipment_id: uuid.UUID | None = None
    aggregate_type: str = "Shipment"
    event_type: str = "ShipmentCancellationRequestedEvent"


@dataclass(frozen=True)
class ShipmentCancelledEvent(
    LogisticsEvent,
    required_fields=("shipment_id",),
    aggregate_id_field="shipment_id",
):
    """Emitted when provider confirms cancellation (CANCEL_PENDING → CANCELLED)."""

    shipment_id: uuid.UUID | None = None
    aggregate_type: str = "Shipment"
    event_type: str = "ShipmentCancelledEvent"


@dataclass(frozen=True)
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


@dataclass(frozen=True)
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


@dataclass(frozen=True)
class ShipmentRecipientUpdatedEvent(
    LogisticsEvent,
    required_fields=("shipment_id",),
    aggregate_id_field="shipment_id",
):
    """Emitted after a successful recipient mutation via /request/edit."""

    shipment_id: uuid.UUID | None = None
    aggregate_type: str = "Shipment"
    event_type: str = "ShipmentRecipientUpdatedEvent"


@dataclass(frozen=True)
class ShipmentDestinationUpdatedEvent(
    LogisticsEvent,
    required_fields=("shipment_id",),
    aggregate_id_field="shipment_id",
):
    """Emitted after a successful destination mutation via /request/edit."""

    shipment_id: uuid.UUID | None = None
    aggregate_type: str = "Shipment"
    event_type: str = "ShipmentDestinationUpdatedEvent"


@dataclass(frozen=True)
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


@dataclass(frozen=True)
class ShipmentEditTaskCompletedEvent(
    LogisticsEvent,
    required_fields=("shipment_id", "task_id"),
    aggregate_id_field="shipment_id",
):
    """Emitted when an async edit task reaches the ``SUCCESS`` terminal state.

    Confirms the carrier-side mutation has been applied — pricing /
    timeline / notification consumers can react to the resulting
    state change. ``kind`` carries the originating
    :class:`EditTaskKind` value so subscribers can route without
    re-reading the shipment.
    """

    shipment_id: uuid.UUID | None = None
    task_id: str | None = None
    kind: str | None = None
    aggregate_type: str = "Shipment"
    event_type: str = "ShipmentEditTaskCompletedEvent"


@dataclass(frozen=True)
class ShipmentEditTaskFailedEvent(
    LogisticsEvent,
    required_fields=("shipment_id", "task_id"),
    aggregate_id_field="shipment_id",
):
    """Emitted when an async edit task reaches the ``FAILURE`` terminal state.

    The provider rejected the mutation — operators must reconcile
    manually (and any optimistic UI update on the storefront must
    be rolled back). ``reason`` captures whatever diagnostic text
    the provider returned, when available.
    """

    shipment_id: uuid.UUID | None = None
    task_id: str | None = None
    kind: str | None = None
    reason: str | None = None
    aggregate_type: str = "Shipment"
    event_type: str = "ShipmentEditTaskFailedEvent"


# ---------------------------------------------------------------------------
# Intake events (CDEK courier pickup)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
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


@dataclass(frozen=True)
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


@dataclass(frozen=True)
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


@dataclass(frozen=True)
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


# ---------------------------------------------------------------------------
# Cross-border (DobroPost) arrival — triggers last-mile shipment creation
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CrossBorderArrivedEvent(
    LogisticsEvent,
    required_fields=("shipment_id",),
    aggregate_id_field="shipment_id",
):
    """Emitted when a cross-border shipment lands at the RF customs / warehouse.

    Triggered by DobroPost ``status_id ∈ {648, 649}`` (see
    ``docs/dobropost_shipment_api/integration.md``). The natural
    subscriber is the order module's last-mile creator: it reads
    ``order_id`` from the event, looks up the customer's chosen pickup
    point and books a Shipment #2 with CDEK / Yandex Delivery.

    Idempotency lives at the consumer (UNIQUE on
    ``order_id × kind="last_mile"``) — the Shipment aggregate also
    guards re-emission via ``cross_border_arrived_at`` so a duplicate
    648/649 webhook does not produce a second event.
    """

    shipment_id: uuid.UUID | None = None
    order_id: uuid.UUID | None = None
    provider_code: str = ""
    provider_status_code: str = ""
    aggregate_type: str = "Shipment"
    event_type: str = "CrossBorderArrivedEvent"


@dataclass(frozen=True)
class ShipmentPassportValidationFailedEvent(
    LogisticsEvent,
    required_fields=("shipment_id",),
    aggregate_id_field="shipment_id",
):
    """Emitted when DobroPost reports ``passportValidationStatus=false``.

    The shipment is **NOT** transitioned to FAILED — it stays BOOKED
    in our local FSM and "hangs" before customs on DobroPost's side
    until the customer supplies corrected passport data. CS uses this
    event to escalate the order; if the data is corrected in time, a
    ``PUT /api/shipment`` resolves the hold. If not, DobroPost
    eventually reports a 544/545 (passport rejected at customs),
    which routes through the regular terminal-failure path.
    """

    shipment_id: uuid.UUID | None = None
    order_id: uuid.UUID | None = None
    aggregate_type: str = "Shipment"
    event_type: str = "ShipmentPassportValidationFailedEvent"
