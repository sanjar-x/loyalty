"""
Yandex Delivery mappers — pure functions for domain ↔ API conversion.

All functions are stateless and side-effect free. They convert between
domain value objects and the JSON structures expected/returned by the
Yandex Delivery "Other Day" API.
"""

import json
import logging
from datetime import UTC, datetime
from typing import Any

from src.modules.logistics.domain.value_objects import (
    PROVIDER_YANDEX_DELIVERY,
    Address,
    BookingRequest,
    BookingResult,
    DeliveryType,
    Money,
    Parcel,
    PickupPoint,
    PickupPointQuery,
    PickupPointType,
    ShippingRate,
    TrackingEvent,
    TrackingStatus,
)
from src.modules.logistics.infrastructure.providers.yandex_delivery.constants import (
    LAST_MILE_COURIER,
    LAST_MILE_PICKUP,
    YANDEX_PICKUP_TYPE_MAP,
    YANDEX_STATUS_MAP,
    parse_pricing_string,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pricing calculator (1.01)
# ---------------------------------------------------------------------------


def build_pricing_request(
    origin: Address,
    destination: Address,
    parcels: list[Parcel],
    tariff: str,
    config: dict[str, Any],
) -> dict[str, Any]:
    """Build request body for POST /pricing-calculator."""
    platform_station_id = origin.metadata.get("platform_station_id") or config.get(
        "platform_station_id", ""
    )

    dest: dict[str, Any] = {}
    dest_station = destination.metadata.get("platform_station_id")
    if dest_station:
        dest["platform_station_id"] = dest_station
    if destination.raw_address:
        dest["address"] = destination.raw_address
    elif destination.street and destination.city:
        dest["address"] = f"{destination.city}, {destination.street}"
        if destination.house:
            dest["address"] += f", {destination.house}"

    total_weight = sum(p.weight.grams for p in parcels)
    total_assessed = sum(
        (p.declared_value.amount if p.declared_value else 0) for p in parcels
    )

    places = []
    for parcel in parcels:
        place: dict[str, Any] = {
            "physical_dims": _build_physical_dims(parcel),
        }
        places.append(place)

    body: dict[str, Any] = {
        "source": {"platform_station_id": platform_station_id},
        "destination": dest,
        "tariff": tariff,
        "total_weight": total_weight,
        "total_assessed_price": total_assessed,
        "client_price": 0,
        "payment_method": config.get("payment_method", "already_paid"),
        "places": places,
    }
    return body


def parse_pricing_response(
    data: dict[str, Any],
    tariff: str,
) -> ShippingRate | None:
    """Parse pricing-calculator response to a ShippingRate.

    Returns ``None`` if the pricing string is missing or unparseable.
    """
    pricing_total = data.get("pricing_total")
    if not pricing_total:
        return None

    try:
        amount, currency = parse_pricing_string(pricing_total)
    except ValueError:
        logger.warning("Failed to parse pricing: %r", pricing_total)
        return None

    delivery_type = (
        DeliveryType.COURIER
        if tariff == LAST_MILE_COURIER
        else DeliveryType.PICKUP_POINT
    )
    delivery_days = data.get("delivery_days")

    return ShippingRate(
        provider_code=PROVIDER_YANDEX_DELIVERY,
        service_code=tariff,
        service_name=f"Yandex Delivery ({tariff})",
        delivery_type=delivery_type,
        total_cost=Money(amount=amount, currency_code=currency),
        base_cost=Money(amount=amount, currency_code=currency),
        delivery_days_min=delivery_days,
        delivery_days_max=delivery_days,
    )


# ---------------------------------------------------------------------------
# Offers create (3.01)
# ---------------------------------------------------------------------------


def build_offers_create_request(
    request: BookingRequest,
    config: dict[str, Any],
) -> dict[str, Any]:
    """Build request body for POST /offers/create."""
    platform_station_id = request.origin.metadata.get(
        "platform_station_id"
    ) or config.get("platform_station_id", "")

    last_mile = (
        LAST_MILE_COURIER
        if request.delivery_type == DeliveryType.COURIER
        else LAST_MILE_PICKUP
    )

    destination = _build_destination(request.destination, last_mile)
    items = _build_items(request, config)
    places = _build_places(request.parcels)

    body: dict[str, Any] = {
        "info": {
            "operator_request_id": str(request.shipment_id),
        },
        "source": {
            "platform_station": {"platform_id": platform_station_id},
        },
        "destination": destination,
        "items": items,
        "places": places,
        "billing_info": {
            "payment_method": config.get("payment_method", "already_paid"),
        },
        "recipient_info": {
            "first_name": request.recipient.first_name,
            "last_name": request.recipient.last_name,
            "phone": request.recipient.phone,
        },
        "last_mile_policy": last_mile,
    }

    if request.recipient.middle_name:
        body["recipient_info"]["patronymic"] = request.recipient.middle_name
    if request.recipient.email:
        body["recipient_info"]["email"] = request.recipient.email

    if request.cod and request.cod.amount.amount > 0:
        body["billing_info"]["delivery_cost"] = request.cod.amount.amount

    return body


def parse_offers_response(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Parse offers/create response, returning raw offer dicts.

    Each offer dict has: offer_id, expires_at, offer_details (with pricing).
    """
    return data.get("offers", [])


# ---------------------------------------------------------------------------
# Offers confirm (3.02)
# ---------------------------------------------------------------------------


def parse_confirm_response(data: dict[str, Any]) -> str:
    """Extract request_id from offers/confirm response."""
    return data["request_id"]


# ---------------------------------------------------------------------------
# Request info (3.03) → BookingResult
# ---------------------------------------------------------------------------


def parse_request_info_to_booking_result(data: dict[str, Any]) -> BookingResult:
    """Parse request/info response into BookingResult."""
    request_id = data.get("request_id", "")

    state = data.get("state", {})
    _ = state.get("description")  # reserved for future use

    return BookingResult(
        provider_shipment_id=request_id,
        tracking_number=data.get("courier_order_id"),
        estimated_delivery=None,
        provider_response_payload=json.dumps(data, ensure_ascii=False, default=str),
    )


# ---------------------------------------------------------------------------
# Tracking history (3.09)
# ---------------------------------------------------------------------------


def parse_tracking_history(data: dict[str, Any]) -> list[TrackingEvent]:
    """Parse request/history response into TrackingEvent list."""
    state_history = data.get("state_history", [])
    events: list[TrackingEvent] = []

    for entry in state_history:
        status_code = entry.get("status", "")
        tracking_status = YANDEX_STATUS_MAP.get(status_code, TrackingStatus.EXCEPTION)

        timestamp = _parse_timestamp(entry)
        if timestamp is None:
            continue

        events.append(
            TrackingEvent(
                status=tracking_status,
                provider_status_code=status_code,
                provider_status_name=entry.get("description", status_code),
                timestamp=timestamp,
                description=entry.get("reason"),
            )
        )

    return events


# ---------------------------------------------------------------------------
# Batch request info (3.04) → tracking
# ---------------------------------------------------------------------------


def parse_batch_requests_info(
    data: dict[str, Any],
) -> dict[str, list[TrackingEvent]]:
    """Parse requests/info batch response into per-shipment tracking events."""
    result: dict[str, list[TrackingEvent]] = {}
    requests = data.get("requests", [])

    for req in requests:
        request_id = req.get("request_id", "")
        state = req.get("state", {})
        if not state:
            result[request_id] = []
            continue

        status_code = state.get("status", "")
        tracking_status = YANDEX_STATUS_MAP.get(status_code, TrackingStatus.EXCEPTION)
        timestamp = _parse_timestamp(state)

        if timestamp is None:
            result[request_id] = []
            continue

        result[request_id] = [
            TrackingEvent(
                status=tracking_status,
                provider_status_code=status_code,
                provider_status_name=state.get("description", status_code),
                timestamp=timestamp,
                description=state.get("reason"),
            )
        ]

    return result


# ---------------------------------------------------------------------------
# Cancel (3.10)
# ---------------------------------------------------------------------------


def parse_cancel_response(data: dict[str, Any]) -> tuple[bool, str | None]:
    """Parse request/cancel response.

    Returns:
        (success, reason) tuple.
    """
    status = data.get("status", "")
    reason = data.get("reason")
    description = data.get("description")

    if status == "SUCCESS":
        return True, None
    if status == "CREATED":
        # Cancellation request created, treated as success
        return True, description
    return False, reason or description or f"Cancel status: {status}"


# ---------------------------------------------------------------------------
# Pickup points (2.02)
# ---------------------------------------------------------------------------


def build_pickup_points_request(
    query: PickupPointQuery,
) -> dict[str, Any]:
    """Build request body for POST /pickup-points/list."""
    body: dict[str, Any] = {}

    if query.latitude is not None and query.longitude is not None:
        radius_deg = (query.radius_km or 10) / 111.0
        body["latitude"] = {
            "from": query.latitude - radius_deg,
            "to": query.latitude + radius_deg,
        }
        body["longitude"] = {
            "from": query.longitude - radius_deg,
            "to": query.longitude + radius_deg,
        }

    if query.delivery_type == DeliveryType.PICKUP_POINT:
        body["type"] = "pickup_point"
    elif query.delivery_type == DeliveryType.POST_OFFICE:
        body["type"] = "terminal"

    return body


def parse_pickup_points(data: dict[str, Any]) -> list[PickupPoint]:
    """Parse pickup-points/list response into PickupPoint list."""
    points = data.get("points", [])
    result: list[PickupPoint] = []

    for pt in points:
        pt_type_str = pt.get("type", "pickup_point")
        mapped_type = YANDEX_PICKUP_TYPE_MAP.get(pt_type_str, "pvz")
        pickup_type = PickupPointType(mapped_type)

        address_data = pt.get("address", {})
        position = pt.get("position", {})

        address = Address(
            country_code=address_data.get("country", "RU")[:2]
            if address_data.get("country")
            else "RU",
            city=address_data.get("locality", ""),
            region=address_data.get("region"),
            postal_code=address_data.get("postal_code"),
            street=address_data.get("street"),
            house=address_data.get("house"),
            apartment=address_data.get("apartment"),
            latitude=position.get("latitude"),
            longitude=position.get("longitude"),
            raw_address=address_data.get("full_address"),
            metadata={"platform_station_id": pt.get("id", "")},
        )

        payment_methods = pt.get("payment_methods", [])
        schedule = pt.get("schedule", {})
        schedule_str = _format_schedule(schedule) if schedule else None

        contact = pt.get("contact", {})
        phone = contact.get("phone") if contact else None

        result.append(
            PickupPoint(
                provider_code=PROVIDER_YANDEX_DELIVERY,
                external_id=pt.get("id", ""),
                name=pt.get("name", ""),
                pickup_point_type=pickup_type,
                address=address,
                work_schedule=schedule_str,
                phone=phone,
                is_cash_allowed="cash" in payment_methods,
                is_card_allowed=(
                    "card_on_receipt" in payment_methods
                    or "already_paid" in payment_methods
                ),
            )
        )

    return result


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _build_destination(
    destination: Address,
    last_mile: str,
) -> dict[str, Any]:
    """Build the ``destination`` block for offers/create or request/create."""
    dest_station = destination.metadata.get("platform_station_id")

    if dest_station and last_mile == LAST_MILE_PICKUP:
        return {
            "type": "platform_station",
            "platform_station": {"platform_id": dest_station},
        }

    dest: dict[str, Any] = {
        "type": "custom_location",
        "custom_location": {
            "details": _build_location_details(destination),
        },
    }
    if destination.latitude is not None and destination.longitude is not None:
        dest["custom_location"]["latitude"] = destination.latitude
        dest["custom_location"]["longitude"] = destination.longitude

    return dest


def _build_location_details(addr: Address) -> dict[str, Any]:
    """Build Yandex ``LocationDetails`` from an Address."""
    details: dict[str, Any] = {}
    if addr.city:
        details["locality"] = addr.city
    if addr.region:
        details["region"] = addr.region
    if addr.street:
        details["street"] = addr.street
    if addr.house:
        details["house"] = addr.house
    if addr.apartment:
        details["apartment"] = addr.apartment
    if addr.postal_code:
        details["postal_code"] = addr.postal_code
    if addr.country_code:
        details["country"] = addr.country_code
    if addr.raw_address:
        details["full_address"] = addr.raw_address
    return details


def _build_items(
    request: BookingRequest,
    config: dict[str, Any],
) -> list[dict[str, Any]]:
    """Build the ``items`` array for offers/create."""
    default_inn = config.get("default_inn", "")
    default_nds = config.get("default_nds", 0)

    items: list[dict[str, Any]] = []
    barcode_idx = 0

    for parcel_idx, parcel in enumerate(request.parcels):
        place_barcode = f"PKG-{parcel_idx + 1:03d}"
        if parcel.items:
            for item in parcel.items:
                unit_price = item.unit_price.amount if item.unit_price else 0
                items.append({
                    "count": item.quantity,
                    "name": item.name,
                    "article": item.sku or f"SKU-{barcode_idx}",
                    "billing_details": {
                        "inn": default_inn,
                        "nds": default_nds,
                        "unit_price": unit_price,
                        "assessed_unit_price": unit_price,
                    },
                    "place_barcode": place_barcode,
                })
                barcode_idx += 1
        else:
            # No items — create a placeholder
            declared = parcel.declared_value.amount if parcel.declared_value else 0
            items.append({
                "count": 1,
                "name": parcel.description or "Товар",
                "article": f"PKG-{parcel_idx + 1:03d}",
                "billing_details": {
                    "inn": default_inn,
                    "nds": default_nds,
                    "unit_price": declared,
                    "assessed_unit_price": declared,
                },
                "place_barcode": place_barcode,
            })

    return items


def _build_places(parcels: list[Parcel]) -> list[dict[str, Any]]:
    """Build the ``places`` array for offers/create."""
    places: list[dict[str, Any]] = []
    for idx, parcel in enumerate(parcels):
        barcode = f"PKG-{idx + 1:03d}"
        places.append({
            "physical_dims": _build_physical_dims(parcel),
            "barcode": barcode,
        })
    return places


def _build_physical_dims(parcel: Parcel) -> dict[str, Any]:
    """Build ``physical_dims`` dict from a Parcel."""
    dims: dict[str, Any] = {
        "weight_gross": parcel.weight.grams,
    }
    if parcel.dimensions:
        dims["dx"] = parcel.dimensions.length_cm
        dims["dy"] = parcel.dimensions.width_cm
        dims["dz"] = parcel.dimensions.height_cm
    return dims


def _parse_timestamp(entry: dict[str, Any]) -> datetime | None:
    """Extract a datetime from a Yandex status entry.

    Prefers ``timestamp_utc`` (ISO string), falls back to ``timestamp`` (UNIX int).
    """
    ts_utc = entry.get("timestamp_utc")
    if ts_utc:
        try:
            dt = datetime.fromisoformat(ts_utc.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=UTC)
            return dt
        except ValueError, AttributeError:
            pass

    ts_unix = entry.get("timestamp")
    if ts_unix is not None:
        try:
            return datetime.fromtimestamp(int(ts_unix), tz=UTC)
        except ValueError, TypeError, OSError:
            pass

    return None


def _format_schedule(schedule: dict[str, Any]) -> str | None:
    """Format a Yandex schedule object to a human-readable string."""
    restrictions = schedule.get("restrictions", [])
    if not restrictions:
        return None

    day_names = {1: "Пн", 2: "Вт", 3: "Ср", 4: "Чт", 5: "Пт", 6: "Сб", 7: "Вс"}
    parts: list[str] = []

    for r in restrictions:
        days = r.get("days", [])
        time_from = r.get("time_from", {})
        time_to = r.get("time_to")

        day_str = ", ".join(day_names.get(d, str(d)) for d in sorted(days))
        from_str = f"{time_from.get('hours', 0):02d}:{time_from.get('minutes', 0):02d}"

        if time_to:
            to_str = f"{time_to.get('hours', 0):02d}:{time_to.get('minutes', 0):02d}"
            parts.append(f"{day_str}: {from_str}–{to_str}")
        else:
            parts.append(f"{day_str}: {from_str}–")

    return "; ".join(parts)
