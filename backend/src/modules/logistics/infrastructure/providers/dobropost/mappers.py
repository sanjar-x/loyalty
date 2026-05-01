"""DobroPost JSON ↔ domain mappers.

* ``build_create_shipment_request`` — domain ``DobroPostShipmentPayload`` →
  HTTP request body (``POST /api/shipment``).
* ``parse_create_shipment_response`` — DobroPost JSON → ``BookingResult``
  (used by ``DobroPostBookingProvider``).
* ``parse_status_update_event`` — webhook payload format №2 →
  ``TrackingEvent``.
* ``parse_list_shipment_response`` — ``GET /api/shipment`` envelope →
  per-shipment list of ``TrackingEvent`` (used by polling provider).
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

from src.modules.logistics.application.commands.dobropost_payload import (
    DobroPostShipmentPayload,
)
from src.modules.logistics.domain.value_objects import (
    BookingResult,
    EstimatedDelivery,
    TrackingEvent,
)
from src.modules.logistics.infrastructure.providers.dobropost.constants import (
    DOBROPOST_INFO_ONLY_STATUS_IDS,
    dobropost_name_to_status_id,
    dobropost_status_to_tracking,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Outbound: domain → DobroPost JSON
# ---------------------------------------------------------------------------


def build_create_shipment_request(payload: DobroPostShipmentPayload) -> dict[str, Any]:
    """Build the body for ``POST /api/shipment`` from domain payload.

    Field names follow ``reference.md`` §2 — camelCase, dates as
    ``YYYY-MM-DD``. ``consigneeMiddleName`` and ``consigneeBirthDate``
    are only included when non-empty (DobroPost rejects null on some
    optional fields).
    """
    rec = payload.recipient
    item = payload.item
    body: dict[str, Any] = {
        "totalAmount": payload.total_amount_cny,
        "consigneeFamilyName": rec.family_name,
        "consigneeName": rec.name,
        "consigneePassportSerial": rec.passport_serial,
        "consigneePassportNumber": rec.passport_number,
        "passportIssueDate": rec.passport_issue_date.isoformat(),
        "vatIdentificationNumber": rec.vat_identification_number,
        "consigneeFullAddress": rec.full_address,
        "consigneeCity": rec.city,
        "consigneeState": rec.state,
        "consigneeZipCode": rec.zip_code,
        "consigneePhoneNumber": rec.phone_number,
        "consigneeEmail": rec.email,
        "itemDescription": item.description,
        "numberOfItemPieces": item.pieces,
        "itemPrice": item.price_cny,
        "itemStoreLink": item.store_link,
        "dpTariffId": payload.dp_tariff_id,
        "incomingDeclaration": payload.incoming_declaration,
    }
    if rec.middle_name:
        body["consigneeMiddleName"] = rec.middle_name
    if rec.birth_date:
        body["consigneeBirthDate"] = rec.birth_date.isoformat()
    if payload.comment:
        body["comment"] = payload.comment
    return body


# ---------------------------------------------------------------------------
# Inbound: DobroPost JSON → domain
# ---------------------------------------------------------------------------


def parse_create_shipment_response(data: dict[str, Any]) -> BookingResult:
    """Convert ``POST /api/shipment`` 200 OK body to ``BookingResult``.

    DobroPost shipment id is integer — we stringify for
    ``provider_shipment_id`` (the column is TEXT).

    ``actual_cost`` is intentionally left ``None``: ``data["totalAmount"]``
    is the **goods value in CNY** (per ``reference.md`` §2 ``totalAmount``
    field — "Общая стоимость товаров Шипмента в юанях"), NOT the shipping
    cost. The shipping tariff is contractual and selected by ``dpTariffId``;
    DobroPost does not return its monetary value in the create response.
    Surfacing CNY-goods-value as ``actual_cost`` would trigger spurious
    "Booking currency mismatch" warnings in ``BookShipmentHandler.
    _verify_actual_cost`` because the shipment's ``quoted_cost`` is RUB.
    """
    dp_id = data.get("id")
    if dp_id is None:
        # Surfaced by booking provider as ProviderHTTPError — kept here
        # so any caller (e.g. test) sees a well-typed BookingResult on
        # the happy path only.
        raise ValueError("DobroPost create response missing 'id'")

    # DobroPost does not return delivery_days in the create response
    # (cross-border ETA is opaque, depending on customs); leave as None.
    estimated: EstimatedDelivery | None = None

    return BookingResult(
        provider_shipment_id=str(dp_id),
        tracking_number=data.get("dptrackNumber") or None,
        estimated_delivery=estimated,
        actual_cost=None,
        provider_response_payload=json.dumps(data, ensure_ascii=False),
    )


def parse_status_update_event(payload: dict[str, Any]) -> TrackingEvent | None:
    """Convert webhook payload format №2 to a unified ``TrackingEvent``.

    Returns ``None`` when the event must be skipped:

    * status name resolves to ``DOBROPOST_INFO_ONLY_STATUS_IDS`` (270-272 —
      edit-shipment dance);
    * status name is not in the dictionary (would otherwise fall back to
      ``TrackingStatus.EXCEPTION`` and force the shipment into FAILED via
      the auto-FSM hook in ``Shipment.append_tracking_event``); a warning
      is logged so the dictionary can be extended.

    Returning ``None`` is preferable to defensive routing: a single
    unknown status string would otherwise cancel an in-flight order.
    """
    raw_status = str(payload.get("status") or "").strip()
    if not raw_status:
        logger.warning("DobroPost webhook: empty status string")
        return None

    status_id = dobropost_name_to_status_id(raw_status)
    if status_id is None:
        logger.warning(
            "DobroPost webhook: unknown status name '%s' — skipping event",
            raw_status,
        )
        return None
    if status_id in DOBROPOST_INFO_ONLY_STATUS_IDS:
        return None

    timestamp = _parse_iso_timestamp(payload.get("statusDate"))
    if timestamp is None:
        return None
    return TrackingEvent(
        status=dobropost_status_to_tracking(status_id),
        provider_status_code=status_id,
        provider_status_name=raw_status,
        timestamp=timestamp,
        location=None,
        description=None,
    )


def parse_list_shipment_response(
    data: dict[str, Any],
) -> dict[str, list[TrackingEvent]]:
    """Convert ``GET /api/shipment`` envelope into per-shipment events.

    Each item in ``content[]`` carries a ``status: {id, name}`` and
    ``statusDate``. We materialise a single ``TrackingEvent`` from the
    *current* state — DobroPost does not expose a status history per
    shipment, so polling effectively backfills missed webhooks.

    The returned dict is keyed by ``provider_shipment_id`` (string of
    integer ``id``).
    """
    out: dict[str, list[TrackingEvent]] = {}
    content = data.get("content") or []
    for item in content:
        if not isinstance(item, dict):
            continue
        dp_id = item.get("id")
        if dp_id is None:
            continue
        status = item.get("status") or {}
        if not isinstance(status, dict):
            continue
        status_id = str(status.get("id") or "")
        status_name = str(status.get("name") or "")
        if not status_id:
            continue
        if status_id in DOBROPOST_INFO_ONLY_STATUS_IDS:
            continue
        # Skip rows where DobroPost omits/garbles statusDate — same
        # rationale as parse_status_update_event: a fake timestamp
        # would corrupt latest_tracking_status ordering.
        timestamp = _parse_iso_timestamp(item.get("statusDate"))
        if timestamp is None:
            continue
        out[str(dp_id)] = [
            TrackingEvent(
                status=dobropost_status_to_tracking(status_id),
                provider_status_code=status_id,
                provider_status_name=status_name,
                timestamp=timestamp,
                location=None,
                description=None,
            )
        ]
    return out


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_iso_timestamp(raw: object) -> datetime | None:
    """Strict ISO 8601 parser.

    Returns ``None`` when the input is missing or malformed. Callers
    must skip the event entirely on ``None`` — substituting ``now()``
    would surface a fake timestamp that becomes ``latest_tracking_status``
    on the aggregate and silently re-orders real history.
    """
    if isinstance(raw, str) and raw:
        try:
            # Python 3.11+ accepts trailing 'Z'
            return datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            logger.warning("DobroPost webhook: bad statusDate '%s'", raw)
    else:
        logger.warning("DobroPost webhook: missing statusDate")
    return None
