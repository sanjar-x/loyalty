"""
CDEK API v2 constants — status mappings, delivery modes, service codes,
webhook event types, and API URLs.

Maps CDEK-native values to unified domain value objects.
Source: CDEK API v2 documentation (Appendices).
"""

from src.modules.logistics.domain.value_objects import (
    DeliveryType,
    TrackingStatus,
)

# ---------------------------------------------------------------------------
# CDEK order status code → unified TrackingStatus
# ---------------------------------------------------------------------------
# CDEK status codes (from "Приложение 15. Статусы заказов"):

CDEK_STATUS_MAP: dict[str, TrackingStatus] = {
    "CREATED": TrackingStatus.CREATED,
    "RECEIVED_AT_SHIPMENT_WAREHOUSE": TrackingStatus.ACCEPTED,
    "READY_FOR_SHIPMENT_IN_SENDER_CITY": TrackingStatus.ACCEPTED,
    "RETURNED_TO_SENDER_CITY_WAREHOUSE": TrackingStatus.EXCEPTION,
    "TAKEN_BY_TRANSPORTER": TrackingStatus.IN_TRANSIT,
    "SENT_TO_TRANSIT_CITY": TrackingStatus.IN_TRANSIT,
    "ACCEPTED_IN_TRANSIT_CITY": TrackingStatus.IN_TRANSIT,
    "ACCEPTED_AT_TRANSIT_WAREHOUSE": TrackingStatus.IN_TRANSIT,
    "RETURNED_TO_TRANSIT_WAREHOUSE": TrackingStatus.EXCEPTION,
    "READY_FOR_SHIPMENT_IN_TRANSIT_CITY": TrackingStatus.IN_TRANSIT,
    "SENT_TO_RECIPIENT_CITY": TrackingStatus.IN_TRANSIT,
    "ACCEPTED_IN_RECIPIENT_CITY": TrackingStatus.IN_TRANSIT,
    "ACCEPTED_AT_RECIPIENT_CITY_WAREHOUSE": TrackingStatus.IN_TRANSIT,
    "ACCEPTED_AT_PICK_UP_POINT": TrackingStatus.READY_FOR_PICKUP,
    "TAKEN_BY_COURIER": TrackingStatus.OUT_FOR_DELIVERY,
    "RETURNED_TO_RECIPIENT_CITY_WAREHOUSE": TrackingStatus.ATTEMPT_FAILED,
    "DELIVERED": TrackingStatus.DELIVERED,
    "NOT_DELIVERED": TrackingStatus.ATTEMPT_FAILED,
    "INVALID": TrackingStatus.EXCEPTION,
    "READY_TO_SHIP_AT_SENDING_OFFICE": TrackingStatus.ACCEPTED,
    "RETURNED_TO_SENDER": TrackingStatus.RETURNED,
    "CUSTOMS_COMPLETE": TrackingStatus.CUSTOMS,
}

# ---------------------------------------------------------------------------
# CDEK delivery_mode → unified DeliveryType
# ---------------------------------------------------------------------------
# CDEK delivery modes (Приложение 15):

CDEK_DELIVERY_MODE_MAP: dict[int, DeliveryType] = {
    1: DeliveryType.COURIER,  # дверь-дверь
    2: DeliveryType.PICKUP_POINT,  # дверь-склад
    3: DeliveryType.COURIER,  # склад-дверь
    4: DeliveryType.PICKUP_POINT,  # склад-склад
    6: DeliveryType.PICKUP_POINT,  # дверь-постамат
    7: DeliveryType.PICKUP_POINT,  # склад-постамат
    8: DeliveryType.COURIER,  # постамат-дверь
    9: DeliveryType.PICKUP_POINT,  # постамат-склад
    10: DeliveryType.PICKUP_POINT,  # постамат-постамат
}


def cdek_status_to_tracking(code: str) -> TrackingStatus:
    """Map a CDEK status code string to a unified TrackingStatus.

    Falls back to ``TrackingStatus.EXCEPTION`` for unknown codes.
    """
    return CDEK_STATUS_MAP.get(code, TrackingStatus.EXCEPTION)


def cdek_delivery_mode_to_type(mode: int) -> DeliveryType:
    """Map a CDEK delivery mode integer to a unified DeliveryType.

    Falls back to ``DeliveryType.COURIER`` for unknown modes.
    """
    return CDEK_DELIVERY_MODE_MAP.get(mode, DeliveryType.COURIER)


# ---------------------------------------------------------------------------
# CDEK API URLs
# ---------------------------------------------------------------------------

CDEK_PRODUCTION_URL = "https://api.cdek.ru"
CDEK_TEST_URL = "https://api.edu.cdek.ru"
CDEK_TOKEN_PATH = "/v2/oauth/token"

# ---------------------------------------------------------------------------
# CDEK order type
# ---------------------------------------------------------------------------
# 1 = интернет-магазин (online store), 2 = доставка (delivery)
CDEK_ORDER_TYPE_ONLINE_STORE = 1
CDEK_ORDER_TYPE_DELIVERY = 2

# ---------------------------------------------------------------------------
# CDEK additional service codes (Приложение 4)
# ---------------------------------------------------------------------------

CDEK_SERVICE_INSURANCE = "INSURANCE"
CDEK_SERVICE_COD = "COD"  # наложенный платёж
CDEK_SERVICE_TRYING_ON = "TRYING_ON"  # примерка на дому
CDEK_SERVICE_PARTIAL_DELIVERY = "PART_DELIV"  # частичная доставка
CDEK_SERVICE_INSPECTION = "INSPECTION"  # осмотр вложения
CDEK_SERVICE_REVERSE = "REVERSE"  # возврат
CDEK_SERVICE_DANGER_CARGO = "DANGER_CARGO"  # опасный груз
CDEK_SERVICE_SMS = "SMS"  # SMS уведомление
CDEK_SERVICE_THERMAL_MODE = "THERMAL_MODE"  # терморежим
CDEK_SERVICE_PACKAGING_1 = "PACKAGE_1"  # упаковка 1
CDEK_SERVICE_BUBBLE_WRAP = "BUBBLE_WRAP"  # пупырчатая плёнка
CDEK_SERVICE_WASTE_PAPER = "WASTE_PAPER"  # макулатурная бумага
CDEK_SERVICE_CARTON_BOX = "CARTON_BOX_XS"  # коробка XS
CDEK_SERVICE_BAN_ATTACHMENT_INSPECTION = "BAN_ATTACHMENT_INSPECTION"

# ---------------------------------------------------------------------------
# CDEK webhook event types
# ---------------------------------------------------------------------------

CDEK_WEBHOOK_ORDER_STATUS = "ORDER_STATUS"
CDEK_WEBHOOK_PRINT_FORM = "PRINT_FORM"
CDEK_WEBHOOK_DOWNLOAD_PHOTO = "DOWNLOAD_PHOTO"
CDEK_WEBHOOK_PREALERT_CLOSED = "PREALERT_CLOSED"
CDEK_WEBHOOK_DELAYED = "DELAYED"
CDEK_WEBHOOK_CD_REQUEST = "CD_REQUEST"
CDEK_WEBHOOK_RECEIVE_FAIL = "RECEIVE_FAIL"

# All webhook types CDEK supports
CDEK_WEBHOOK_TYPES = frozenset({
    CDEK_WEBHOOK_ORDER_STATUS,
    CDEK_WEBHOOK_PRINT_FORM,
    CDEK_WEBHOOK_DOWNLOAD_PHOTO,
    CDEK_WEBHOOK_PREALERT_CLOSED,
    CDEK_WEBHOOK_DELAYED,
    CDEK_WEBHOOK_CD_REQUEST,
    CDEK_WEBHOOK_RECEIVE_FAIL,
})

# ---------------------------------------------------------------------------
# CDEK intake statuses
# ---------------------------------------------------------------------------

CDEK_INTAKE_STATUS_ACCEPTED = "ACCEPTED"
CDEK_INTAKE_STATUS_WAITING = "WAITING"
CDEK_INTAKE_STATUS_DELAYED = "DELAYED"
CDEK_INTAKE_STATUS_COMPLETED = "COMPLETED"
CDEK_INTAKE_STATUS_CANCELLED = "CANCELLED"

# ---------------------------------------------------------------------------
# CDEK currency codes (Приложение 11)
# ---------------------------------------------------------------------------

CDEK_CURRENCY_RUB = 1
CDEK_CURRENCY_KZT = 2
CDEK_CURRENCY_USD = 3
CDEK_CURRENCY_EUR = 4
CDEK_CURRENCY_GBP = 5
CDEK_CURRENCY_CNY = 6
CDEK_CURRENCY_BYN = 7
CDEK_CURRENCY_UAH = 8
CDEK_CURRENCY_KGS = 9
CDEK_CURRENCY_AMD = 10
CDEK_CURRENCY_TRY = 11
CDEK_CURRENCY_THB = 12
CDEK_CURRENCY_KRW = 13
CDEK_CURRENCY_AED = 14
CDEK_CURRENCY_UZS = 15
CDEK_CURRENCY_MNT = 16
CDEK_CURRENCY_PLN = 17
CDEK_CURRENCY_AZN = 18
CDEK_CURRENCY_GEL = 19
CDEK_CURRENCY_JPY = 50

# ---------------------------------------------------------------------------
# CDEK print form types
# ---------------------------------------------------------------------------

CDEK_PRINT_WAYBILL = "waybill"
CDEK_PRINT_BARCODE = "barcode"
