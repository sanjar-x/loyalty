"""
Yandex Delivery constants — status mappings, API URLs, helpers.

All Yandex Delivery "Other Day" (межгород) statuses are mapped to
the unified ``TrackingStatus`` enum.  Both door-delivery and pickup
status flows are covered.
"""

from src.modules.logistics.domain.value_objects import TrackingStatus

# ---------------------------------------------------------------------------
# API hosts
# ---------------------------------------------------------------------------

YANDEX_PRODUCTION_URL = "https://b2b-authproxy.taxi.yandex.net"
YANDEX_TEST_URL = "https://b2b.taxi.tst.yandex.net"

# ---------------------------------------------------------------------------
# API paths
# ---------------------------------------------------------------------------

PATH_PRICING_CALCULATOR = "/api/b2b/platform/pricing-calculator"
PATH_OFFERS_INFO_GET = "/api/b2b/platform/offers/info"
PATH_OFFERS_INFO_POST = "/api/b2b/platform/offers/info"
PATH_OFFERS_CREATE = "/api/b2b/platform/offers/create"
PATH_OFFERS_CONFIRM = "/api/b2b/platform/offers/confirm"
PATH_REQUEST_INFO = "/api/b2b/platform/request/info"
PATH_REQUESTS_INFO = "/api/b2b/platform/requests/info"
PATH_REQUEST_ACTUAL_INFO = "/api/b2b/platform/request/actual_info"
PATH_REQUEST_EDIT = "/api/b2b/platform/request/edit"
PATH_REQUEST_HISTORY = "/api/b2b/platform/request/history"
PATH_REQUEST_CANCEL = "/api/b2b/platform/request/cancel"
PATH_REQUEST_CREATE = "/api/b2b/platform/request/create"
PATH_LOCATION_DETECT = "/api/b2b/platform/location/detect"
PATH_PICKUP_POINTS_LIST = "/api/b2b/platform/pickup-points/list"
PATH_GENERATE_LABELS = "/api/b2b/platform/request/generate-labels"
PATH_HANDOVER_ACT = "/api/b2b/platform/request/get-handover-act"

# ---------------------------------------------------------------------------
# Yandex status → unified TrackingStatus
# ---------------------------------------------------------------------------

YANDEX_STATUS_MAP: dict[str, TrackingStatus] = {
    # --- Initial / validation ---
    "DRAFT": TrackingStatus.CREATED,
    "VALIDATING": TrackingStatus.CREATED,
    "VALIDATING_ERROR": TrackingStatus.EXCEPTION,
    # --- Accepted / processing ---
    "CREATED": TrackingStatus.ACCEPTED,
    "DELIVERY_PROCESSING_STARTED": TrackingStatus.ACCEPTED,
    "DELIVERY_TRACK_RECIEVED": TrackingStatus.ACCEPTED,  # Yandex typo
    # --- Sorting center (in transit) ---
    "SORTING_CENTER_PROCESSING_STARTED": TrackingStatus.IN_TRANSIT,
    "SORTING_CENTER_TRACK_RECEIVED": TrackingStatus.IN_TRANSIT,
    "SORTING_CENTER_TRACK_LOADED": TrackingStatus.IN_TRANSIT,
    "SORTING_CENTER_LOADED": TrackingStatus.IN_TRANSIT,
    "SORTING_CENTER_AT_START": TrackingStatus.IN_TRANSIT,
    "SORTING_CENTER_PREPARED": TrackingStatus.IN_TRANSIT,
    "SORTING_CENTER_TRANSMITTED": TrackingStatus.IN_TRANSIT,
    # --- Delivery in transit ---
    "DELIVERY_LOADED": TrackingStatus.IN_TRANSIT,
    "DELIVERY_AT_START": TrackingStatus.IN_TRANSIT,
    "DELIVERY_AT_START_SORT": TrackingStatus.IN_TRANSIT,
    "DELIVERY_TRANSPORTATION": TrackingStatus.IN_TRANSIT,
    # --- Out for delivery ---
    "DELIVERY_TRANSPORTATION_RECIPIENT": TrackingStatus.OUT_FOR_DELIVERY,
    # --- Ready for pickup ---
    "DELIVERY_ARRIVED_PICKUP_POINT": TrackingStatus.READY_FOR_PICKUP,
    "DELIVERY_STORAGE_PERIOD_EXTENDED": TrackingStatus.READY_FOR_PICKUP,
    "CONFIRMATION_CODE_RECEIVED": TrackingStatus.READY_FOR_PICKUP,
    # --- Delivered ---
    "DELIVERY_TRANSMITTED_TO_RECIPIENT": TrackingStatus.DELIVERED,
    "DELIVERY_DELIVERED": TrackingStatus.DELIVERED,
    "PARTICULARLY_DELIVERED": TrackingStatus.DELIVERED,
    "FINISHED": TrackingStatus.DELIVERED,
    # --- Delivery failed ---
    "DELIVERY_ATTEMPT_FAILED": TrackingStatus.ATTEMPT_FAILED,
    "DELIVERY_STORAGE_PERIOD_EXPIRED": TrackingStatus.ATTEMPT_FAILED,
    # --- Returns ---
    "SORTING_CENTER_RETURN_PREPARING": TrackingStatus.RETURNED,
    "SORTING_CENTER_RETURN_PREPARING_SENDER": TrackingStatus.RETURNED,
    "SORTING_CENTER_RETURN_ARRIVED": TrackingStatus.RETURNED,
    "SORTING_CENTER_RETURN_RETURNED": TrackingStatus.RETURNED,
    "RETURN_PREPARING": TrackingStatus.RETURNED,
    "RETURN_TRANSPORTATION_STARTED": TrackingStatus.RETURNED,
    "RETURN_ARRIVED_DELIVERY": TrackingStatus.RETURNED,
    "RETURN_TRANSMITTED_FULFILMENT": TrackingStatus.RETURNED,
    "RETURN_READY_FOR_PICKUP": TrackingStatus.RETURNED,
    "RETURN_RETURNED": TrackingStatus.RETURNED,
    # --- Cancellation / exceptions ---
    "CANCELLED": TrackingStatus.CANCELLED,
    "CANCELED_IN_PLATFORM": TrackingStatus.CANCELLED,
    # --- Order modifications (treat as in-transit) ---
    "DELIVERY_UPDATED_BY_SHOP": TrackingStatus.IN_TRANSIT,
    "DELIVERY_UPDATED_BY_RECIPIENT": TrackingStatus.IN_TRANSIT,
    "DELIVERY_UPDATED_BY_DELIVERY": TrackingStatus.IN_TRANSIT,
}

# ---------------------------------------------------------------------------
# Delivery type mappings
# ---------------------------------------------------------------------------

LAST_MILE_COURIER = "time_interval"
LAST_MILE_PICKUP = "self_pickup"

# ---------------------------------------------------------------------------
# Pickup station type → PickupPointType
# ---------------------------------------------------------------------------

YANDEX_PICKUP_TYPE_MAP: dict[str, str] = {
    "pickup_point": "pvz",
    "terminal": "postamat",
    "warehouse": "terminal",
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def parse_pricing_string(pricing: str) -> tuple[int, str]:
    """Parse Yandex pricing string like ``"225.7 RUB"`` to (kopecks, currency).

    Tolerates locale variations Yandex may emit:
    - ``"1 234.56 RUB"`` — thousands separator (NBSP / regular space)
    - ``"225,70 RUB"`` — comma as decimal separator
    - ``"225 RUB"`` — integer without decimals

    Returns:
        Tuple of (amount_in_smallest_unit, currency_code).
        E.g. ``"1 400.96 RUB"`` → ``(140096, "RUB")``.

    Raises:
        ValueError: If the pricing string contains no recognisable number
            or no 3-letter currency suffix.
    """
    # The currency suffix is always 3 ASCII letters; everything before it
    # is the (possibly thousands-separated) amount.
    cleaned = pricing.strip().replace(" ", " ")
    if len(cleaned) < 4 or not cleaned[-3:].isalpha():
        raise ValueError(f"Invalid pricing format (no currency): {pricing!r}")
    currency = cleaned[-3:].upper()
    amount_str = cleaned[:-3].strip()
    if not amount_str:
        raise ValueError(f"Invalid pricing format (no amount): {pricing!r}")

    # Strip thousands separators and normalise decimal separator.
    normalised = amount_str.replace(" ", "").replace(",", ".")
    try:
        amount_float = float(normalised)
    except ValueError as exc:
        raise ValueError(f"Invalid pricing format (bad amount): {pricing!r}") from exc

    amount_kopecks = round(amount_float * 100)
    return amount_kopecks, currency
