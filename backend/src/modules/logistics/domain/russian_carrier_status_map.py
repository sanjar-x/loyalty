"""Map unified ``TrackingStatus`` → russian-carrier action for Order FSM.

The order side consumes a small canonical action vocabulary
(``RussianCarrierTrackingConsumer``):

* ``IN_TRANSIT`` / ``OUT_FOR_DELIVERY`` → ``MarkOrderInLastMile``
* ``AT_PICKUP_POINT`` → ``MarkOrderAwaitingPickup``
* ``DELIVERED`` → ``MarkOrderDelivered``
* ``RETURN_TO_SENDER`` / ``REFUSED`` / ``FAILURE`` → ``MarkOrderReturningToWarehouse``

Provider adapters (CDEK, Yandex Delivery, Russian Post, Boxberry) ALREADY
normalise their native status codes into the unified
``TrackingStatus`` enum at the point they construct ``TrackingEvent``
(see ``logistics.domain.value_objects.TrackingStatus`` + each provider
adapter's ``parse_events``). This module is therefore a *single*
TrackingStatus → canonical-action mapping rather than per-provider
tables — the per-provider work has already happened upstream.

Any russian (i.e. non-DobroPost) carrier therefore funnels through the
same mapping. ``provider_code`` is accepted as an argument only so a
future asymmetry (e.g. Boxberry's "ATTEMPTED" semantics) can be
introduced without changing call sites.

References:
* CDEK status reference — ``docs/local_logistics/cdek-statuses.md``
  (source: https://api-docs.cdek.ru/29923849.html)
* Yandex Delivery — see ``logistics.infrastructure.providers.yandex.adapter``
  (status mapping in ``_to_unified_status``)
* Russian Post — ``docs/local_logistics/russian-post-statuses.md``
"""

from __future__ import annotations

from enum import StrEnum

from src.modules.logistics.domain.value_objects import (
    PROVIDER_DOBROPOST,
    ProviderCode,
    TrackingStatus,
)


class RussianCarrierAction(StrEnum):
    """Canonical action vocabulary consumed by ``RussianCarrierTrackingConsumer``.

    Values match what the consumer's ``normalized.upper()`` branch already
    accepts — keep these strings stable or update the consumer in lockstep.
    """

    IN_LAST_MILE = "IN_TRANSIT"
    """Carrier picked up the parcel from the RU warehouse and started
    transit — Order moves ARRIVED_IN_RU → IN_LAST_MILE."""

    OUT_FOR_DELIVERY = "OUT_FOR_DELIVERY"
    """Courier en route with the parcel today — same Order action as
    ``IN_LAST_MILE``; preserved as a distinct action so analytics can
    differentiate."""

    AT_PICKUP_POINT = "AT_PICKUP_POINT"
    """Parcel arrived at the customer's pickup point and is waiting for
    pickup — Order moves IN_LAST_MILE → AWAITING_PICKUP."""

    DELIVERED = "DELIVERED"
    """Customer picked the parcel up — Order moves AWAITING_PICKUP →
    DELIVERED."""

    RETURN_TO_SENDER = "RETURN_TO_SENDER"
    """Parcel is being returned to the RU warehouse (storage timeout,
    customer refused, undeliverable address). Order moves to
    RETURNING_TO_RU_WAREHOUSE."""


# TrackingStatus → action.
#
# Statuses NOT in this map produce ``None`` → no Order FSM action.
# Reasoning per omitted status:
# - CREATED / ACCEPTED — pre-pickup, irrelevant to the russian-carrier
#   leg (the booking handler already flipped the Shipment to BOOKED).
# - CUSTOMS — only relevant to cross-border (DobroPost), not russian
#   carriers. If a russian carrier emits it (rare), no FSM move is
#   safe — Shipment-level tracking is enough.
# - LOST / EXCEPTION — Shipment aggregate already auto-transitions to
#   ``ShipmentStatus.FAILED`` via ``mark_failed_from_tracking``; we
#   surface a RETURN_TO_SENDER on EXCEPTION so the Order goes through
#   the returning flow, which terminates in NOT_DELIVERED via cron.
# - ATTEMPT_FAILED — transient retry (carrier will re-attempt). No
#   FSM move; the next attempt's status carries the real outcome.
# - CANCELLED — carrier-side cancellation; Shipment already auto-
#   transitions to CANCELLED. Order's CancelOrder is the path for
#   carrier-driven Order-level cancellation (separate event flow).
_STATUS_TO_ACTION: dict[TrackingStatus, RussianCarrierAction] = {
    TrackingStatus.IN_TRANSIT: RussianCarrierAction.IN_LAST_MILE,
    TrackingStatus.OUT_FOR_DELIVERY: RussianCarrierAction.OUT_FOR_DELIVERY,
    TrackingStatus.READY_FOR_PICKUP: RussianCarrierAction.AT_PICKUP_POINT,
    TrackingStatus.DELIVERED: RussianCarrierAction.DELIVERED,
    TrackingStatus.RETURNED: RussianCarrierAction.RETURN_TO_SENDER,
    # EXCEPTION on a russian carrier (lost-in-transit, damaged, undeliverable)
    # routes through the returning flow rather than the failure flow because
    # the Order side has no terminal "delivery_failed" state — it has
    # NOT_DELIVERED reachable via RETURNING_TO_RU_WAREHOUSE.
    TrackingStatus.EXCEPTION: RussianCarrierAction.RETURN_TO_SENDER,
}


def russian_carrier_status_map(
    status: TrackingStatus,
    provider_code: ProviderCode,
) -> RussianCarrierAction | None:
    """Map a unified tracking status to a russian-carrier Order action.

    Returns ``None`` for:
    * DobroPost shipments — the cross-border webhook ingest pipeline
      (``order.application.commands.ingest_dobropost_webhook``) owns
      Order FSM moves for that provider.
    * Statuses that don't correspond to any Order FSM move (see the
      omission rationale on ``_STATUS_TO_ACTION``).

    Args:
        status: Unified tracking status as emitted by the provider's
            adapter (already normalised — see module docstring).
        provider_code: Provider that emitted the status. DobroPost
            shipments are filtered here so the same ingest path can
            run safely for every provider.

    Returns:
        The canonical :class:`RussianCarrierAction` consumed by the
        Order side, or ``None`` if no Order FSM action is appropriate.
    """
    if provider_code == PROVIDER_DOBROPOST:
        return None
    return _STATUS_TO_ACTION.get(status)


__all__ = [
    "RussianCarrierAction",
    "russian_carrier_status_map",
]
