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
    ShipmentDestinationUpdatedEvent,
    ShipmentEditTaskCompletedEvent,
    ShipmentEditTaskFailedEvent,
    ShipmentEditTaskScheduledEvent,
    ShipmentIntakeScheduledEvent,
    ShipmentRecipientUpdatedEvent,
    ShipmentRefusalRegisteredEvent,
    ShipmentReturnRegisteredEvent,
    ShipmentTrackingUpdatedEvent,
)
from src.modules.logistics.domain.exceptions import InvalidShipmentTransitionError
from src.modules.logistics.domain.value_objects import (
    TERMINAL_CANCEL_TRACKING_STATUSES,
    TERMINAL_FAILURE_TRACKING_STATUSES,
    Address,
    CashOnDelivery,
    ContactInfo,
    DeliveryQuote,
    DeliveryType,
    EditTaskKind,
    EditTaskStatus,
    EstimatedDelivery,
    IntakeStatus,
    Money,
    Parcel,
    PendingEditTask,
    ProviderCode,
    RegisteredReturn,
    ScheduledIntake,
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
            # Idempotent retry of BOOKING_PENDING is handled by
            # ``mark_booking_pending`` short-circuiting *before*
            # ``_transition_to`` — it never reaches the table.
            ShipmentStatus.BOOKED,
            ShipmentStatus.FAILED,
            # Auto-transition from terminal carrier statuses ingested
            # while booking is still pending (e.g. webhook reports
            # NOT_DELIVERED before the polling window resolves).
            ShipmentStatus.CANCELLED,
        }
    ),
    ShipmentStatus.BOOKED: frozenset(
        {
            ShipmentStatus.CANCEL_PENDING,
            # Carrier-initiated terminal outcomes ingested via tracking events.
            ShipmentStatus.FAILED,
            ShipmentStatus.CANCELLED,
        }
    ),
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

    # Outstanding async edit tasks (Yandex 3.06 / 3.12 / 3.14 / 3.15).
    # The list is short — at most one entry per kind in flight — and is
    # cleared as the status-poller observes terminal states.
    pending_edit_tasks: list[PendingEditTask] = attrs.Factory(list)

    # Currently-active courier intake (CDEK). At most one at a time:
    # cancelling clears, scheduling overwrites.
    scheduled_intake: ScheduledIntake | None = None

    # Provider-side returns / refusals registered against this shipment.
    # Append-only audit list — multiple refusals are technically possible
    # if the courier retries with a new recipient.
    registered_returns: list[RegisteredReturn] = attrs.Factory(list)

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
        """Create a new shipment in DRAFT status from a selected DeliveryQuote.

        The quote's ``delivery_days_min`` / ``delivery_days_max`` are
        seeded into ``estimated_delivery`` immediately so they survive
        even when the booking response (e.g. CDEK's ``GET /v2/orders``)
        omits them — the booking phase only enriches the estimate with
        an exact ``estimated_date`` when the carrier provides one.
        """
        now = datetime.now(UTC)
        initial_estimate: EstimatedDelivery | None = None
        if (
            quote.rate.delivery_days_min is not None
            or quote.rate.delivery_days_max is not None
        ):
            initial_estimate = EstimatedDelivery(
                min_days=quote.rate.delivery_days_min,
                max_days=quote.rate.delivery_days_max,
            )
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
            estimated_delivery=initial_estimate,
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
        """Transition DRAFT → BOOKING_PENDING (idempotent on retry).

        A retry from an already-pending shipment is treated as a no-op:
        no FSM state change, no domain event emitted, no version bump —
        the original BOOKING_PENDING event still applies. This lets the
        ``BookShipmentHandler`` be safely re-invoked after a provider
        polling timeout left the shipment in BOOKING_PENDING.
        """
        if self.status == ShipmentStatus.BOOKING_PENDING:
            return
        self._transition_to(ShipmentStatus.BOOKING_PENDING)
        self.add_domain_event(ShipmentBookingRequestedEvent(shipment_id=self.id))

    def mark_booked(
        self,
        provider_shipment_id: str,
        tracking_number: str | None = None,
        estimated_delivery: EstimatedDelivery | None = None,
    ) -> None:
        """Transition BOOKING_PENDING → BOOKED.

        ``provider_shipment_id`` and ``tracking_number`` use *merge*
        semantics — a non-empty new value overrides, but an empty /
        ``None`` argument keeps whatever was previously set. This
        prevents idempotent retries (e.g. CDEK polls where the second
        response omits ``cdek_number``) from clobbering data the first
        booking response captured.

        ``estimated_delivery`` is merged field-by-field via
        :func:`_merge_estimates` so ``min_days`` / ``max_days`` from
        the quote survive a booking response that only echoes
        ``estimated_date``.
        """
        self._transition_to(ShipmentStatus.BOOKED)
        if provider_shipment_id:
            self.provider_shipment_id = provider_shipment_id
        if tracking_number:
            self.tracking_number = tracking_number
        self.estimated_delivery = _merge_estimates(
            self.estimated_delivery, estimated_delivery
        )
        self.booked_at = datetime.now(UTC)
        # Clear any failure_reason left over from a previous failed cancel
        # attempt — the shipment is now successfully (re)booked.
        self.failure_reason = None
        self.add_domain_event(
            ShipmentBookedEvent(
                shipment_id=self.id,
                provider_shipment_id=provider_shipment_id,
                tracking_number=tracking_number,
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
        """Transition BOOKED → CANCEL_PENDING.

        Clears any ``failure_reason`` left over from a previous failed
        cancel attempt — a successful (re)cancellation must not
        surface stale error text downstream.
        """
        self._transition_to(ShipmentStatus.CANCEL_PENDING)
        self.failure_reason = None
        self.add_domain_event(ShipmentCancellationRequestedEvent(shipment_id=self.id))

    def mark_cancelled(self) -> None:
        """Transition CANCEL_PENDING → CANCELLED."""
        self._transition_to(ShipmentStatus.CANCELLED)
        self.cancelled_at = datetime.now(UTC)
        # Cancellation succeeded — drop any failure note from a prior
        # rejected cancel attempt so consumers don't read it as the
        # cancellation reason.
        self.failure_reason = None
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

    def mark_failed_from_tracking(self, reason: str) -> None:
        """Transition to FAILED on a terminal carrier failure (LOST / EXCEPTION).

        Used by ``append_tracking_event`` when the ingested status implies
        the shipment cannot be delivered. Idempotent — already-FAILED
        shipments are silently ignored.
        """
        if self.status == ShipmentStatus.FAILED:
            return
        self._transition_to(ShipmentStatus.FAILED)
        self.failure_reason = reason
        self.add_domain_event(
            ShipmentBookingFailedEvent(shipment_id=self.id, reason=reason)
        )

    def mark_cancelled_from_tracking(self, reason: str | None = None) -> None:
        """Transition to CANCELLED when the carrier itself cancelled the order.

        No provider API call is required — the cancellation has already
        happened on the carrier side. Idempotent on already-CANCELLED
        shipments.
        """
        if self.status == ShipmentStatus.CANCELLED:
            return
        self._transition_to(ShipmentStatus.CANCELLED)
        self.cancelled_at = datetime.now(UTC)
        if reason is not None:
            self.failure_reason = reason
        self.add_domain_event(ShipmentCancelledEvent(shipment_id=self.id))

    # -- Tracking -----------------------------------------------------------

    def append_tracking_event(self, event: TrackingEvent) -> None:
        """Append a new tracking event from the carrier.

        Deduplicates by (timestamp, status) to ensure idempotency when the
        same event arrives via webhook and polling. If a duplicate carries
        a more detailed ``location`` or ``description`` than the original,
        the stored event is replaced in-place (without bumping the version
        or emitting a new event).

        ``latest_tracking_status`` is always recomputed from the most-recent
        timestamp across *all* events to prevent regression when out-of-order
        events arrive.
        """
        for idx, existing in enumerate(self.tracking_events):
            if (
                existing.timestamp == event.timestamp
                and existing.status == event.status
            ):
                # Upgrade with richer info if the new event has more data
                # in any optional field; skip otherwise (idempotent).
                if _has_richer_info(existing, event):
                    self.tracking_events[idx] = event
                    self.updated_at = datetime.now(UTC)
                return

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

        # Auto-transition the local FSM on terminal carrier outcomes.
        # Applies to *every* non-terminal state — including
        # BOOKING_PENDING, where a webhook can race ahead of the
        # polling window and report ``NOT_DELIVERED`` / ``LOST``
        # before the booking adapter ever observes ``statuses``.
        if self.status not in (
            ShipmentStatus.CANCELLED,
            ShipmentStatus.FAILED,
        ):
            if event.status in TERMINAL_FAILURE_TRACKING_STATUSES:
                fail_reason = (
                    event.description
                    or event.provider_status_name
                    or event.status.value
                )
                self.mark_failed_from_tracking(reason=fail_reason)
            elif event.status in TERMINAL_CANCEL_TRACKING_STATUSES:
                cancel_reason: str | None = (
                    event.description or event.provider_status_name or None
                )
                self.mark_cancelled_from_tracking(reason=cancel_reason)

    # -- Edit / mutation operations ----------------------------------------

    def apply_recipient_change(self, recipient: ContactInfo) -> None:
        """Replace the recipient locally after a successful provider edit.

        Emits :class:`ShipmentRecipientUpdatedEvent` so downstream
        consumers (notifications, cart re-sync) react to the change.
        """
        if self.recipient == recipient:
            return
        self.recipient = recipient
        self.updated_at = datetime.now(UTC)
        self.version += 1
        self.add_domain_event(ShipmentRecipientUpdatedEvent(shipment_id=self.id))

    def apply_destination_change(
        self,
        destination: Address,
        *,
        delivery_type: DeliveryType | None = None,
    ) -> None:
        """Replace the destination locally after a successful provider edit.

        ``delivery_type`` may also have changed (e.g. courier → pickup
        point swap on Yandex 3.06); when supplied it overrides the
        previous value.
        """
        if self.destination == destination and (
            delivery_type is None or self.delivery_type == delivery_type
        ):
            return
        self.destination = destination
        if delivery_type is not None:
            self.delivery_type = delivery_type
        self.updated_at = datetime.now(UTC)
        self.version += 1
        self.add_domain_event(ShipmentDestinationUpdatedEvent(shipment_id=self.id))

    def record_edit_task(
        self,
        task_id: str,
        kind: EditTaskKind,
        *,
        initial_status: EditTaskStatus = EditTaskStatus.PENDING,
    ) -> None:
        """Record an outstanding async edit task.

        Replaces any previous task of the same kind — at most one of
        each kind is in flight at a time. Emits
        :class:`ShipmentEditTaskScheduledEvent` so the status-poller
        / consumers know to start watching ``task_id``.
        """
        self.pending_edit_tasks = [t for t in self.pending_edit_tasks if t.kind != kind]
        self.pending_edit_tasks.append(
            PendingEditTask(
                task_id=task_id,
                kind=kind,
                submitted_at=datetime.now(UTC),
                initial_status=initial_status,
            )
        )
        self.updated_at = datetime.now(UTC)
        self.version += 1
        self.add_domain_event(
            ShipmentEditTaskScheduledEvent(
                shipment_id=self.id,
                task_id=task_id,
                kind=kind.value,
            )
        )

    def settle_edit_task(
        self,
        task_id: str,
        status: EditTaskStatus,
        *,
        reason: str | None = None,
    ) -> None:
        """Drop a previously-recorded edit task once it reaches a terminal state.

        Called by the status-poller. ``status`` must be a terminal
        :class:`EditTaskStatus` (``SUCCESS`` or ``FAILURE``); other values
        are rejected so non-terminal polls do not strip the task.

        Idempotent on unknown ``task_id`` — no state change, no event.
        Emits :class:`ShipmentEditTaskCompletedEvent` on ``SUCCESS`` or
        :class:`ShipmentEditTaskFailedEvent` on ``FAILURE`` so consumers
        can react to terminal outcomes without polling the poller.
        """
        if status not in (EditTaskStatus.SUCCESS, EditTaskStatus.FAILURE):
            raise ValueError(
                "settle_edit_task requires a terminal status "
                "(SUCCESS or FAILURE), got " + status.value
            )
        settled = next(
            (t for t in self.pending_edit_tasks if t.task_id == task_id),
            None,
        )
        if settled is None:
            return
        self.pending_edit_tasks = [
            t for t in self.pending_edit_tasks if t.task_id != task_id
        ]
        self.updated_at = datetime.now(UTC)
        self.version += 1
        if status == EditTaskStatus.SUCCESS:
            self.add_domain_event(
                ShipmentEditTaskCompletedEvent(
                    shipment_id=self.id,
                    task_id=task_id,
                    kind=settled.kind.value,
                )
            )
        else:
            self.add_domain_event(
                ShipmentEditTaskFailedEvent(
                    shipment_id=self.id,
                    task_id=task_id,
                    kind=settled.kind.value,
                    reason=reason,
                )
            )

    # -- Intake (CDEK courier pickup) --------------------------------------

    def record_intake(
        self,
        provider_intake_id: str,
        *,
        status: IntakeStatus = IntakeStatus.ACCEPTED,
    ) -> None:
        """Attach an active courier intake to the shipment.

        Overwrites any previous intake — only one is in flight at a
        time. Emits :class:`ShipmentIntakeScheduledEvent`.
        """
        self.scheduled_intake = ScheduledIntake(
            provider_intake_id=provider_intake_id,
            status=status,
            scheduled_at=datetime.now(UTC),
        )
        self.updated_at = datetime.now(UTC)
        self.version += 1
        self.add_domain_event(
            ShipmentIntakeScheduledEvent(
                shipment_id=self.id,
                provider_intake_id=provider_intake_id,
                intake_status=status.value,
            )
        )

    def clear_intake(self) -> None:
        """Drop the recorded intake without emitting an event.

        The intake-cancel flow does not have a Shipment context (the
        command takes only ``provider_code`` + ``provider_intake_id``)
        so the event is emitted by the handler against an
        ``Intake`` aggregate via :class:`ShipmentIntakeCancelledEvent`.
        Use this method when the cancel handler *did* manage to
        correlate the intake back to a Shipment (rare path).
        """
        if self.scheduled_intake is None:
            return
        self.scheduled_intake = None
        self.updated_at = datetime.now(UTC)
        self.version += 1

    # -- Returns / refusals -------------------------------------------------

    def record_return(
        self,
        provider_return_id: str | None,
        *,
        reason: str | None = None,
    ) -> None:
        """Append a successful client-return registration."""
        self.registered_returns.append(
            RegisteredReturn(
                kind="client_return",
                provider_return_id=provider_return_id,
                reason=reason,
                registered_at=datetime.now(UTC),
            )
        )
        self.updated_at = datetime.now(UTC)
        self.version += 1
        self.add_domain_event(
            ShipmentReturnRegisteredEvent(
                shipment_id=self.id,
                provider_return_id=provider_return_id,
            )
        )

    def record_refusal(self, reason: str | None = None) -> None:
        """Append a successful doorstep-refusal registration."""
        self.registered_returns.append(
            RegisteredReturn(
                kind="refusal",
                reason=reason,
                registered_at=datetime.now(UTC),
            )
        )
        self.updated_at = datetime.now(UTC)
        self.version += 1
        self.add_domain_event(
            ShipmentRefusalRegisteredEvent(
                shipment_id=self.id,
                reason=reason,
            )
        )


def _merge_estimates(
    base: EstimatedDelivery | None, override: EstimatedDelivery | None
) -> EstimatedDelivery | None:
    """Combine quote-time and booking-time estimates field-by-field.

    Each non-None field on ``override`` wins; otherwise the value from
    ``base`` is kept. Returns ``None`` when both inputs are ``None`` or
    when the resulting estimate carries no information.
    """
    if base is None and override is None:
        return None
    if base is None:
        return override
    if override is None:
        return base
    merged = EstimatedDelivery(
        min_days=override.min_days if override.min_days is not None else base.min_days,
        max_days=override.max_days if override.max_days is not None else base.max_days,
        estimated_date=override.estimated_date or base.estimated_date,
    )
    if (
        merged.min_days is None
        and merged.max_days is None
        and merged.estimated_date is None
    ):
        return None
    return merged


def _has_richer_info(existing: TrackingEvent, candidate: TrackingEvent) -> bool:
    """Return True if *candidate* has more populated optional fields than *existing*.

    Used by ``Shipment.append_tracking_event`` to decide whether to replace
    a previously-recorded event with a duplicate that carries extra context.
    """
    for field in ("location", "description"):
        old_val = getattr(existing, field)
        new_val = getattr(candidate, field)
        if not old_val and new_val:
            return True
        # Prefer the longer description (more verbose carrier text)
        if old_val and new_val and len(new_val) > len(old_val):
            return True
    return False
