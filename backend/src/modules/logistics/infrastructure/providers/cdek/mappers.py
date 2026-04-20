"""
CDEK ↔ domain mappers — pure functions for building CDEK API requests
and parsing CDEK API responses into domain value objects.

All money conversions: domain uses kopecks (int), CDEK uses rubles (float).
Weight: CDEK uses grams (int) = domain convention — no conversion needed.
Dimensions: CDEK uses centimeters (int) = domain convention — no conversion needed.
"""

import json
import logging
import uuid
from datetime import UTC, datetime

from src.modules.logistics.domain.value_objects import (
    PROVIDER_CDEK,
    Address,
    BookingRequest,
    BookingResult,
    ContactInfo,
    DeliveryQuote,
    DeliveryType,
    Dimensions,
    EstimatedDelivery,
    Money,
    Parcel,
    ParcelItem,
    PickupPoint,
    PickupPointQuery,
    PickupPointType,
    ShippingRate,
    TrackingEvent,
)
from src.modules.logistics.infrastructure.providers.cdek.constants import (
    CDEK_ORDER_TYPE_ONLINE_STORE,
    CDEK_SERVICE_COD,
    CDEK_SERVICE_INSURANCE,
    cdek_delivery_mode_to_type,
    cdek_status_to_tracking,
)
from src.modules.logistics.infrastructure.providers.errors import (
    ProviderHTTPError,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_RUB = "RUB"
_CDEK_CURRENCY_RUB = 1  # CDEK numeric currency code for RUB


def _kopecks_to_rubles(kopecks: int) -> float:
    """Convert domain kopecks to CDEK rubles."""
    return round(kopecks / 100, 2)


def _rubles_to_kopecks(rubles: float) -> int:
    """Convert CDEK rubles to domain kopecks."""
    return round(rubles * 100)


def _parse_cdek_datetime(value: str) -> datetime:
    """Parse CDEK datetime string (ISO-like with timezone)."""
    # CDEK returns: "2025-01-15T10:30:00+0300" or "2025-01-15T10:30:00+03:00"
    cleaned = value.strip()
    try:
        return datetime.fromisoformat(cleaned)
    except ValueError:
        # Handle "+0300" format (no colon)
        if len(cleaned) >= 5 and cleaned[-5] in ("+", "-") and ":" not in cleaned[-5:]:
            cleaned = cleaned[:-2] + ":" + cleaned[-2:]
        return datetime.fromisoformat(cleaned)


def _parse_cdek_date(value: str) -> datetime | None:
    """Parse a CDEK date string (``YYYY-MM-DD``) to a UTC datetime, or None."""
    try:
        return datetime.strptime(value.strip(), "%Y-%m-%d").replace(tzinfo=UTC)
    except ValueError, AttributeError:
        return None


def _check_cdek_errors(data: dict, context: str) -> None:
    """Raise ``ProviderHTTPError`` if the CDEK response contains errors."""
    errors = data.get("errors")
    if not errors:
        return
    msgs = "; ".join(f"{e.get('code', '?')}: {e.get('message', '?')}" for e in errors)
    raise ProviderHTTPError(
        status_code=400,
        message=f"CDEK {context} error: {msgs}",
        response_body=json.dumps(data, ensure_ascii=False, default=str),
    )


# ---------------------------------------------------------------------------
# Calculator request/response mappers
# ---------------------------------------------------------------------------


def _build_calc_location(address: Address) -> dict:
    """Build a CDEK calculator location from an Address VO."""
    loc: dict = {}
    if address.metadata.get("cdek_city_code"):
        loc["code"] = int(address.metadata["cdek_city_code"])
    elif address.postal_code:
        loc["postal_code"] = address.postal_code
    else:
        loc["address"] = address.raw_address or address.city
        if address.country_code:
            loc["country_code"] = address.country_code
    return loc


def build_calculator_request(
    origin: Address,
    destination: Address,
    parcels: list[Parcel],
) -> dict:
    """Build CDEK ``/v2/calculator/tarifflist`` request body."""
    packages = []
    for parcel in parcels:
        pkg: dict = {"weight": parcel.weight.grams}
        if parcel.dimensions:
            pkg["length"] = parcel.dimensions.length_cm
            pkg["width"] = parcel.dimensions.width_cm
            pkg["height"] = parcel.dimensions.height_cm
        packages.append(pkg)

    return {
        "type": CDEK_ORDER_TYPE_ONLINE_STORE,
        "currency": _CDEK_CURRENCY_RUB,
        "from_location": _build_calc_location(origin),
        "to_location": _build_calc_location(destination),
        "packages": packages,
    }


def parse_tariff_list_response(data: dict) -> list[DeliveryQuote]:
    """Parse CDEK ``/v2/calculator/tarifflist`` response into DeliveryQuote list.

    Raises ``ProviderHTTPError`` if the response contains ``errors``.
    Logs any ``warnings`` from the CDEK response.
    """
    _check_cdek_errors(data, "calculator")

    warnings = data.get("warnings")
    if warnings:
        for w in warnings:
            logger.warning(
                "CDEK calculator warning: %s — %s",
                w.get("code", "?"),
                w.get("message", "?"),
            )

    quotes: list[DeliveryQuote] = []
    now = datetime.now(UTC)

    for tariff in data.get("tariff_codes") or []:
        tariff_code = tariff.get("tariff_code")
        if tariff_code is None:
            continue

        delivery_sum = tariff.get("delivery_sum", 0)
        delivery_mode = tariff.get("delivery_mode", 1)
        delivery_type = cdek_delivery_mode_to_type(delivery_mode)

        rate = ShippingRate(
            provider_code=PROVIDER_CDEK,
            service_code=str(tariff_code),
            service_name=tariff.get("tariff_name", f"CDEK tariff {tariff_code}"),
            delivery_type=delivery_type,
            total_cost=Money(
                amount=_rubles_to_kopecks(delivery_sum), currency_code=_RUB
            ),
            base_cost=Money(
                amount=_rubles_to_kopecks(delivery_sum), currency_code=_RUB
            ),
            delivery_days_min=tariff.get("period_min"),
            delivery_days_max=tariff.get("period_max"),
        )

        payload = json.dumps({
            "tariff_code": tariff_code,
            "delivery_mode": delivery_mode,
            "tariff_name": tariff.get("tariff_name"),
            "tariff_description": tariff.get("tariff_description"),
            "calendar_min": tariff.get("calendar_min"),
            "calendar_max": tariff.get("calendar_max"),
        })

        quotes.append(
            DeliveryQuote(
                id=uuid.uuid4(),
                rate=rate,
                provider_payload=payload,
                quoted_at=now,
                expires_at=None,
            )
        )

    return quotes


# ---------------------------------------------------------------------------
# Order request/response mappers
# ---------------------------------------------------------------------------


def build_order_request(request: BookingRequest) -> dict:
    """Build CDEK ``POST /v2/orders`` request body from a BookingRequest."""
    payload_data = (
        json.loads(request.provider_payload) if request.provider_payload else {}
    )
    tariff_code = payload_data.get("tariff_code")
    if tariff_code is None:
        tariff_code = int(request.service_code)

    body: dict = {
        "type": CDEK_ORDER_TYPE_ONLINE_STORE,
        "number": str(request.shipment_id),
        "tariff_code": tariff_code,
        "recipient": _build_contact(request.recipient),
        "packages": _build_packages(request.parcels),
    }

    if request.sender:
        body["sender"] = _build_contact(request.sender)

    # Location handling: use delivery_point or to_location based on delivery type
    if request.delivery_type == DeliveryType.PICKUP_POINT:
        delivery_point_code = request.destination.metadata.get("cdek_pvz_code")
        if delivery_point_code:
            body["delivery_point"] = delivery_point_code
        else:
            body["to_location"] = _build_location(request.destination)
    else:
        body["to_location"] = _build_location(request.destination)

    shipment_point_code = request.origin.metadata.get("cdek_pvz_code")
    if shipment_point_code:
        body["shipment_point"] = shipment_point_code
    else:
        body["from_location"] = _build_location(request.origin)

    # COD (cash on delivery)
    if request.cod:
        body["delivery_recipient_cost"] = {
            "value": _kopecks_to_rubles(request.cod.amount.amount),
        }
        body.setdefault("services", []).append({
            "code": CDEK_SERVICE_COD,
            "parameter": str(_kopecks_to_rubles(request.cod.amount.amount)),
        })

    # Declared value → insurance service
    if request.declared_value:
        body.setdefault("services", []).append({
            "code": CDEK_SERVICE_INSURANCE,
            "parameter": str(_kopecks_to_rubles(request.declared_value.amount)),
        })

    return body


def _build_contact(contact: ContactInfo) -> dict:
    """Build a CDEK contact dict from a ContactInfo VO."""
    result: dict = {"name": contact.full_name}
    if contact.phone:
        result["phones"] = [{"number": contact.phone}]
    if contact.email:
        result["email"] = contact.email
    if contact.company_name:
        result["company"] = contact.company_name
    return result


def _build_location(address: Address) -> dict:
    """Build a CDEK location dict from an Address VO."""
    loc: dict = {}
    if address.metadata.get("cdek_city_code"):
        loc["code"] = int(address.metadata["cdek_city_code"])
    if address.metadata.get("fias_guid"):
        loc["fias_guid"] = address.metadata["fias_guid"]
    if address.postal_code:
        loc["postal_code"] = address.postal_code
    if address.country_code:
        loc["country_code"] = address.country_code
    if address.city:
        loc["city"] = address.city
    if address.region:
        loc["region"] = address.region

    parts = []
    if address.street:
        parts.append(address.street)
    if address.house:
        parts.append(f"д. {address.house}")
    if address.apartment:
        parts.append(f"кв. {address.apartment}")
    loc["address"] = ", ".join(parts) if parts else address.raw_address or address.city

    if address.latitude is not None and address.longitude is not None:
        loc["latitude"] = address.latitude
        loc["longitude"] = address.longitude

    return loc


def _build_packages(parcels: list[Parcel]) -> list[dict]:
    """Build CDEK packages list from domain Parcels."""
    packages = []
    for i, parcel in enumerate(parcels, start=1):
        pkg: dict = {
            "number": str(i),
            "weight": parcel.weight.grams,
        }
        if parcel.dimensions:
            pkg["length"] = parcel.dimensions.length_cm
            pkg["width"] = parcel.dimensions.width_cm
            pkg["height"] = parcel.dimensions.height_cm
        if parcel.description:
            pkg["comment"] = parcel.description
        if parcel.items:
            count = len(parcel.items)
            pkg["items"] = [_build_item(item, parcel, count) for item in parcel.items]
        packages.append(pkg)
    return packages


def _build_item(item: ParcelItem, parcel: Parcel, item_count: int) -> dict:
    """Build a CDEK package item dict from a ParcelItem.

    ``cost`` is REQUIRED by CDEK — defaults to 0 if ``unit_price`` is absent.
    ``weight`` falls back to parcel weight divided by item count (not full parcel).
    """
    if item.weight:
        item_weight = item.weight.grams
    else:
        item_weight = max(1, parcel.weight.grams // max(1, item_count))

    cost = _kopecks_to_rubles(item.unit_price.amount) if item.unit_price else 0
    payment_value = cost

    result: dict = {
        "name": item.name,
        "ware_key": item.sku or str(uuid.uuid4())[:8],
        "cost": cost,
        "payment": {"value": payment_value},
        "weight": item_weight,
        "amount": item.quantity,
    }
    if item.country_of_origin:
        result["country_code"] = item.country_of_origin
    if item.hs_code:
        result["feacn_code"] = item.hs_code
    return result


def parse_order_create_response(data: dict) -> tuple[str, list[dict]]:
    """Parse CDEK order creation response.

    Returns (entity_uuid, requests_list).
    CDEK returns 202 with:
    ``{"entity": {"uuid": "..."}, "requests": [{"request_uuid": "...", ...}]}``
    """
    entity = data.get("entity", {})
    entity_uuid = entity.get("uuid", "")
    requests = data.get("requests", [])
    return entity_uuid, requests


def parse_order_info_response(data: dict) -> BookingResult:
    """Parse CDEK ``GET /v2/orders/{uuid}`` into a BookingResult.

    Extracts delivery estimates from multiple CDEK fields:
    - ``delivery_detail.date`` — actual delivery date
    - ``planned_delivery_date`` — estimated delivery date
    - ``delivery_detail.period_min/period_max`` — delivery period in days
    """
    entity = data.get("entity", data)
    provider_shipment_id = entity.get("uuid", "")
    cdek_number = entity.get("cdek_number")
    tracking_number = str(cdek_number) if cdek_number else None

    delivery_detail = entity.get("delivery_detail") or {}
    period_min = delivery_detail.get("period_min")
    period_max = delivery_detail.get("period_max")

    # Try exact delivery date from delivery_detail or planned_delivery_date
    estimated_date: datetime | None = None
    delivery_date_str = delivery_detail.get("date")
    if delivery_date_str:
        estimated_date = _parse_cdek_date(delivery_date_str)
    if estimated_date is None:
        planned_str = entity.get("planned_delivery_date")
        if planned_str:
            estimated_date = _parse_cdek_date(planned_str)

    estimated_delivery = None
    if period_min is not None or period_max is not None or estimated_date is not None:
        estimated_delivery = EstimatedDelivery(
            min_days=period_min,
            max_days=period_max,
            estimated_date=estimated_date,
        )

    return BookingResult(
        provider_shipment_id=provider_shipment_id,
        tracking_number=tracking_number,
        estimated_delivery=estimated_delivery,
        provider_response_payload=json.dumps(data, ensure_ascii=False, default=str),
    )


# ---------------------------------------------------------------------------
# Tracking event mapper
# ---------------------------------------------------------------------------


def parse_tracking_events(statuses: list[dict]) -> list[TrackingEvent]:
    """Parse CDEK order statuses into domain TrackingEvent list."""
    events: list[TrackingEvent] = []
    for status in statuses:
        code = status.get("code", "")
        if status.get("deleted"):
            continue
        timestamp_str = status.get("date_time")
        if not timestamp_str:
            continue
        events.append(
            TrackingEvent(
                status=cdek_status_to_tracking(code),
                provider_status_code=code,
                provider_status_name=status.get("name", ""),
                timestamp=_parse_cdek_datetime(timestamp_str),
                location=status.get("city"),
                description=status.get("name"),
            )
        )
    return events


# ---------------------------------------------------------------------------
# Pickup point mapper
# ---------------------------------------------------------------------------


def _parse_office_dimensions(office: dict) -> Dimensions | None:
    """Extract max dimension limit from a CDEK OfficeDto.

    CDEK offices have TWO dimension sources:
    1. Top-level ``length_max``, ``width_max``, ``height_max`` (floats, cm)
    2. ``dimensions`` array (for postamats with multiple cell sizes)

    We prefer top-level fields (covers both PVZ and postamats),
    falling back to the largest cell from the ``dimensions`` array.
    """
    # Prefer top-level fields — available for both PVZ and postamats
    length_max = office.get("length_max")
    width_max = office.get("width_max")
    height_max = office.get("height_max")
    if length_max and width_max and height_max:
        return Dimensions(
            length_cm=int(length_max),
            width_cm=int(width_max),
            height_cm=int(height_max),
        )

    # Fallback: largest cell from dimensions array (postamats)
    raw_dims = office.get("dimensions")
    if raw_dims and isinstance(raw_dims, list) and raw_dims:
        dims = [d for d in raw_dims if isinstance(d, dict)]
        if dims:
            biggest = max(
                dims,
                key=lambda d: (
                    d.get("width", 0) * d.get("height", 0) * d.get("depth", 0)
                ),
            )
            if biggest.get("width") and biggest.get("height") and biggest.get("depth"):
                return Dimensions(
                    length_cm=int(biggest["depth"]),
                    width_cm=int(biggest["width"]),
                    height_cm=int(biggest["height"]),
                )
    return None


def parse_delivery_points(data: list[dict]) -> list[PickupPoint]:
    """Parse CDEK ``GET /v2/deliverypoints`` response into PickupPoint list."""
    points: list[PickupPoint] = []
    for office in data:
        location = office.get("location", {})
        office_type = office.get("type", "PVZ")
        pp_type = (
            PickupPointType.POSTAMAT
            if office_type == "POSTAMAT"
            else PickupPointType.PVZ
        )

        metadata: dict[str, str] = {}
        city_code = location.get("city_code")
        if city_code is not None:
            metadata["cdek_city_code"] = str(city_code)
        fias_guid = location.get("fias_guid")
        if fias_guid:
            metadata["fias_guid"] = fias_guid
        office_code = office.get("code")
        if office_code:
            metadata["cdek_pvz_code"] = office_code

        address = Address(
            country_code=location.get("country_code", "RU"),
            city=location.get("city", ""),
            region=location.get("region"),
            postal_code=location.get("postal_code"),
            latitude=location.get("latitude"),
            longitude=location.get("longitude"),
            raw_address=location.get("address_full") or location.get("address"),
            metadata=metadata,
        )

        phones = office.get("phones", [])
        phone = phones[0].get("number") if phones else None

        # weight_max is in kg (float), domain uses grams
        weight_max = office.get("weight_max")
        weight_limit = round(weight_max * 1000) if weight_max is not None else None
        weight_min = office.get("weight_min")
        if weight_min is not None and weight_limit is not None and weight_min > 0:
            metadata["weight_min_grams"] = str(int(weight_min * 1000))

        points.append(
            PickupPoint(
                provider_code=PROVIDER_CDEK,
                external_id=office.get("code", ""),
                name=office.get("name")
                or office.get("address_comment")
                or office.get("code", ""),
                pickup_point_type=pp_type,
                address=address,
                work_schedule=office.get("work_time"),
                phone=phone,
                is_cash_allowed=office.get("have_cash", False),
                is_card_allowed=office.get("have_cashless", False),
                weight_limit_grams=weight_limit,
                dimensions_limit=_parse_office_dimensions(office),
            )
        )
    return points


# ---------------------------------------------------------------------------
# Delivery point query params mapper
# ---------------------------------------------------------------------------


def build_delivery_points_params(
    query: PickupPointQuery,
    *,
    page: int | None = None,
    page_size: int | None = None,
) -> dict:
    """Build CDEK ``GET /v2/deliverypoints`` query params.

    Maps domain PickupPointQuery fields to all supported CDEK params:
    postal_code, city, country_code, type, latitude/longitude, etc.
    Supports pagination via ``page``/``size`` params.
    """
    params: dict = {}
    if query.postal_code:
        params["postal_code"] = query.postal_code
    if query.city:
        params["city"] = query.city
    if query.country_code:
        params["country_code"] = query.country_code

    if query.delivery_type == DeliveryType.PICKUP_POINT:
        params["type"] = "PVZ"
        params["is_handout"] = "true"
    elif query.delivery_type == DeliveryType.COURIER:
        params["is_reception"] = "true"

    if query.latitude is not None and query.longitude is not None:
        params["latitude"] = query.latitude
        params["longitude"] = query.longitude
        if query.radius_km is not None:
            params["radius"] = query.radius_km

    if page is not None:
        params["page"] = page
    if page_size is not None:
        params["size"] = page_size

    return params


# ---------------------------------------------------------------------------
# Webhook event mapper
# ---------------------------------------------------------------------------


def parse_webhook_body(body: bytes) -> list[tuple[str, list[TrackingEvent]]]:
    """Parse CDEK ORDER_STATUS webhook body.

    CDEK sends::

        {
            "type": "ORDER_STATUS",
            "date_time": "...",
            "uuid": "...",
            "attributes": {
                "is_return": false,
                "cdek_number": "...",
                "number": "...",
                "status_code": "...",
                "status_date_time": "...",
                "city_name": "...",
                "code": "..."
            }
        }

    Returns list of (provider_shipment_id, [TrackingEvent]).
    """
    data = json.loads(body)
    webhook_attrs = data.get("attributes", {})
    cdek_uuid = data.get("uuid", "")
    status_code = webhook_attrs.get("status_code", webhook_attrs.get("code", ""))
    status_datetime = webhook_attrs.get("status_date_time") or data.get("date_time", "")

    if not status_code or not cdek_uuid:
        return []

    event = TrackingEvent(
        status=cdek_status_to_tracking(status_code),
        provider_status_code=status_code,
        provider_status_name=webhook_attrs.get("status_reason_code", status_code),
        timestamp=_parse_cdek_datetime(status_datetime),
        location=webhook_attrs.get("city_name"),
        description=None,
    )
    return [(cdek_uuid, [event])]
