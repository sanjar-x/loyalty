"""
CDEK API v2 constants — status mappings, delivery modes, service codes,
webhook event types, and API URLs.

Maps CDEK-native values to unified domain value objects.
Source: CDEK API v2 documentation (Appendices).
"""

import structlog

from src.modules.logistics.domain.value_objects import (
    DeliveryType,
    TrackingStatus,
)

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# CDEK order status code → unified TrackingStatus
# ---------------------------------------------------------------------------
# CDEK status codes (from "Приложение 15. Статусы заказов"):

CDEK_STATUS_MAP: dict[str, TrackingStatus] = {
    # ----- Inbound at sender side ----------------------------------------
    "CREATED": TrackingStatus.CREATED,
    "REGISTERED": TrackingStatus.CREATED,
    "ACCEPTED": TrackingStatus.ACCEPTED,
    "RECEIVED_AT_SHIPMENT_WAREHOUSE": TrackingStatus.ACCEPTED,
    "READY_TO_SHIP_AT_SENDING_OFFICE": TrackingStatus.ACCEPTED,
    "READY_FOR_SHIPMENT_IN_SENDER_CITY": TrackingStatus.ACCEPTED,
    # ----- In transit ----------------------------------------------------
    "TAKEN_BY_TRANSPORTER": TrackingStatus.IN_TRANSIT,
    "TAKEN_BY_TRANSPORTER_FROM_SENDER_CITY": TrackingStatus.IN_TRANSIT,
    "TAKEN_BY_TRANSPORTER_FROM_TRANSIT_CITY": TrackingStatus.IN_TRANSIT,
    "SENT_TO_TRANSIT_CITY": TrackingStatus.IN_TRANSIT,
    "ACCEPTED_IN_TRANSIT_CITY": TrackingStatus.IN_TRANSIT,
    "ACCEPTED_AT_TRANSIT_WAREHOUSE": TrackingStatus.IN_TRANSIT,
    "READY_FOR_SHIPMENT_IN_TRANSIT_CITY": TrackingStatus.IN_TRANSIT,
    "SENT_TO_RECIPIENT_CITY": TrackingStatus.IN_TRANSIT,
    "ACCEPTED_IN_RECIPIENT_CITY": TrackingStatus.IN_TRANSIT,
    "ACCEPTED_AT_RECIPIENT_CITY_WAREHOUSE": TrackingStatus.IN_TRANSIT,
    "PASSED_TO_TRANSIT_CARRIER": TrackingStatus.IN_TRANSIT,
    "SHIPPED_TO_DESTINATION": TrackingStatus.IN_TRANSIT,
    # ----- Customs -------------------------------------------------------
    "IN_CUSTOMS_INTERNATIONAL": TrackingStatus.CUSTOMS,
    "IN_CUSTOMS_LOCAL": TrackingStatus.CUSTOMS,
    "IN_CUSTOMS_NEW": TrackingStatus.CUSTOMS,
    "SUBMITTED_TO_CUSTOMS": TrackingStatus.CUSTOMS,
    # ``RELEASED_BY_CUSTOMS*`` and ``CUSTOMS_COMPLETE`` mean clearance is
    # finished and the parcel is moving on, not "currently at customs".
    "RELEASED_BY_CUSTOMS": TrackingStatus.IN_TRANSIT,
    "RELEASED_BY_CUSTOMS_LOCAL": TrackingStatus.IN_TRANSIT,
    "CUSTOMS_COMPLETE": TrackingStatus.IN_TRANSIT,
    # ----- At pickup-point / postamat ------------------------------------
    "ACCEPTED_AT_PICK_UP_POINT": TrackingStatus.READY_FOR_PICKUP,
    "POSTOMAT_POSTED": TrackingStatus.READY_FOR_PICKUP,
    "POSTOMAT_SEIZED": TrackingStatus.IN_TRANSIT,
    "POSTOMAT_RECEIVED": TrackingStatus.DELIVERED,
    # ----- On the way to the recipient -----------------------------------
    "TAKEN_BY_COURIER": TrackingStatus.OUT_FOR_DELIVERY,
    "TAKEN_BY_COURIER_FROM_WAREHOUSE": TrackingStatus.OUT_FOR_DELIVERY,
    # ----- Final / terminal ---------------------------------------------
    "DELIVERED": TrackingStatus.DELIVERED,
    # ATTEMPT_FAILED — the courier tried, did not hand the parcel over,
    # and the order will be retried automatically. RETURNED_TO_RECIPIENT
    # is the warehouse round-trip that follows a failed attempt.
    "RETURNED_TO_RECIPIENT_CITY_WAREHOUSE": TrackingStatus.ATTEMPT_FAILED,
    # Carrier-side terminal failures (cannot deliver, address invalid, etc.)
    # — FSM transitions the shipment to FAILED.
    "NOT_DELIVERED": TrackingStatus.EXCEPTION,
    "INVALID": TrackingStatus.EXCEPTION,
    "DELETED": TrackingStatus.CANCELLED,
    # Reverse / return flow
    "RETURNED_TO_SENDER": TrackingStatus.RETURNED,
    # Both warehouse-arrival statuses on the return leg are *waystations*,
    # not terminal failures — the parcel is still in motion and may reach
    # ``RETURNED_TO_SENDER`` (terminal) afterwards. Mapping them to
    # ``EXCEPTION`` used to auto-FAIL the shipment via
    # ``Shipment.append_tracking_event`` and emit a spurious
    # ``ShipmentDeliveryFailedEvent`` even though the return was going well.
    "RETURNED_TO_SENDER_CITY_WAREHOUSE": TrackingStatus.IN_TRANSIT,
    "RETURNED_TO_TRANSIT_WAREHOUSE": TrackingStatus.IN_TRANSIT,
    "SENT_TO_SENDER_CITY": TrackingStatus.IN_TRANSIT,
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

    Unknown codes fall back to ``TrackingStatus.IN_TRANSIT`` (non-terminal)
    so CDEK extending Приложение 1 with a new status does not auto-FAIL
    every shipment that hits it via the auto-transition hook in
    ``Shipment.append_tracking_event``. A structured warning is emitted
    instead so the gap can be closed by extending ``CDEK_STATUS_MAP``.
    This mirrors the Yandex Delivery mapper's deliberate non-terminal
    fallback (``yandex_delivery/mappers.py``).
    """
    status = CDEK_STATUS_MAP.get(code)
    if status is None:
        logger.warning("cdek_unknown_status_code", code=code)
        return TrackingStatus.IN_TRANSIT
    return status


def cdek_delivery_mode_to_type(mode: int) -> DeliveryType:
    """Map a CDEK delivery mode integer to a unified DeliveryType.

    Falls back to ``DeliveryType.COURIER`` for unknown modes.
    """
    return CDEK_DELIVERY_MODE_MAP.get(mode, DeliveryType.COURIER)


# ---------------------------------------------------------------------------
# CDEK status code → human-readable name (Приложение 1)
# ---------------------------------------------------------------------------
# The ORDER_STATUS webhook payload carries only the status ``code`` — no
# human name. Polling (``GET /v2/orders``) does include ``name``, but
# this map lets the webhook path produce a meaningful
# ``provider_status_name`` too instead of echoing the raw code.

CDEK_STATUS_NAME_MAP: dict[str, str] = {
    "ACCEPTED": "Принят",
    "CREATED": "Создан",
    "REMOVED": "Удалён",
    "RECEIVED_AT_SHIPMENT_WAREHOUSE": "Принят на склад отправителя",
    "READY_FOR_SHIPMENT_IN_SENDER_CITY": "Готов к отправке в городе-отправителе",
    "TAKEN_BY_TRANSPORTER_FROM_SENDER_CITY": "Сдан перевозчику в городе-отправителе",
    "SENT_TO_RECIPIENT_CITY": "Отправлен в город-получатель",
    "ACCEPTED_IN_RECIPIENT_CITY": "Встречен в городе-получателе",
    "ACCEPTED_AT_RECIPIENT_CITY_WAREHOUSE": "Принят на склад доставки",
    "TAKEN_BY_COURIER": "Выдан на доставку",
    "ACCEPTED_AT_PICK_UP_POINT": "Принят на склад до востребования",
    "DELIVERED": "Вручён",
    "NOT_DELIVERED": "Не вручён",
    "ACCEPTED_AT_TRANSIT_WAREHOUSE": "Принят на склад транзита",
    "RETURNED_TO_SENDER_CITY_WAREHOUSE": "Возвращён на склад отправителя",
    "RETURNED_TO_TRANSIT_WAREHOUSE": "Возвращён на склад транзита",
    "RETURNED_TO_RECIPIENT_CITY_WAREHOUSE": "Возвращён на склад доставки",
    "READY_FOR_SHIPMENT_IN_TRANSIT_CITY": "Выдан на отправку в городе-транзите",
    "TAKEN_BY_TRANSPORTER_FROM_TRANSIT_CITY": "Сдан перевозчику в городе-транзите",
    "SENT_TO_TRANSIT_CITY": "Отправлен в город-транзит",
    "ACCEPTED_IN_TRANSIT_CITY": "Встречен в городе-транзите",
    "SENT_TO_SENDER_CITY": "Отправлен в город-отправитель",
    "ACCEPTED_IN_SENDER_CITY": "Встречен в городе-отправителе",
    "ENTERED_TO_TRANSIT_WAREHOUSE": "Поступил в город транзита",
    "ENTERED_TO_RECIPIENT_CITY_WAREHOUSE": "Поступил на склад доставки",
    "ENTERED_TO_PICK_UP_POINT": "Поступил на склад до востребования",
    "IN_CUSTOMS_INTERNATIONAL": "Таможенное оформление в стране отправления",
    "SHIPPED_TO_DESTINATION": "Отправлено в страну назначения",
    "PASSED_TO_TRANSIT_CARRIER": "Передано транзитному перевозчику",
    "IN_CUSTOMS_LOCAL": "Таможенное оформление в стране назначения",
    "CUSTOMS_COMPLETE": "Таможенное оформление завершено",
    "POSTOMAT_POSTED": "Заложен в постамат",
    "POSTOMAT_SEIZED": "Изъят из постамата курьером",
    "POSTOMAT_RECEIVED": "Изъят из постамата клиентом",
    "INVALID": "Некорректный заказ",
}


def cdek_status_name(code: str, fallback: str | None = None) -> str:
    """Return the human-readable name for a CDEK status ``code``.

    Falls back to ``fallback`` (or the raw code) for codes not in
    Приложение 1 — used by the webhook path which has no ``name`` field.
    """
    return CDEK_STATUS_NAME_MAP.get(code) or fallback or code


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
# Source: CDEK API v2 ``WebhookDto`` enum + "Описание структуры вебхуков".
# The legacy ``DOWNLOAD_PHOTO`` / ``DELAYED`` / ``CD_REQUEST`` /
# ``RECEIVE_FAIL`` codes no longer exist in the current protocol.

CDEK_WEBHOOK_ORDER_STATUS = "ORDER_STATUS"  # смена статуса заказа
CDEK_WEBHOOK_ORDER_MODIFIED = "ORDER_MODIFIED"  # изменение заказа (цена/дата/режим)
CDEK_WEBHOOK_PRINT_FORM = "PRINT_FORM"  # готовность печатной формы
CDEK_WEBHOOK_RECEIPT = "RECEIPT"  # чек
CDEK_WEBHOOK_PREALERT_CLOSED = "PREALERT_CLOSED"  # закрытие преалерта
CDEK_WEBHOOK_ACCOMPANYING_WAYBILL = "ACCOMPANYING_WAYBILL"  # транспорт для СНТ
CDEK_WEBHOOK_OFFICE_AVAILABILITY = "OFFICE_AVAILABILITY"  # доступность офиса
CDEK_WEBHOOK_DELIV_PROBLEM = "DELIV_PROBLEM"  # проблема доставки по заказу
CDEK_WEBHOOK_DELIV_AGREEMENT = "DELIV_AGREEMENT"  # изменение договорённости о доставке
CDEK_WEBHOOK_COURIER_INFO = "COURIER_INFO"  # данные назначенного курьера

# All webhook types CDEK supports
CDEK_WEBHOOK_TYPES = frozenset(
    {
        CDEK_WEBHOOK_ORDER_STATUS,
        CDEK_WEBHOOK_ORDER_MODIFIED,
        CDEK_WEBHOOK_PRINT_FORM,
        CDEK_WEBHOOK_RECEIPT,
        CDEK_WEBHOOK_PREALERT_CLOSED,
        CDEK_WEBHOOK_ACCOMPANYING_WAYBILL,
        CDEK_WEBHOOK_OFFICE_AVAILABILITY,
        CDEK_WEBHOOK_DELIV_PROBLEM,
        CDEK_WEBHOOK_DELIV_AGREEMENT,
        CDEK_WEBHOOK_COURIER_INFO,
    }
)

# Webhook types we auto-subscribe to at registry bootstrap. CDEK caps a
# client at 2 active subscriptions ("не более двух подписок"), so we
# register only the two that drive the Shipment aggregate: live carrier
# status changes and order modifications (price / planned-date / mode
# drift). The remaining types stay available for manual admin wiring.
CDEK_WEBHOOK_AUTO_SUBSCRIBE: tuple[str, ...] = (
    CDEK_WEBHOOK_ORDER_STATUS,
    CDEK_WEBHOOK_ORDER_MODIFIED,
)

# Maximum concurrent webhook subscriptions allowed per CDEK client.
CDEK_MAX_WEBHOOK_SUBSCRIPTIONS = 2

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
CDEK_CURRENCY_JPY = 55  # Приложение 14: Йена = 55 (не 50)
CDEK_CURRENCY_VND = 704

# ISO 4217 alpha-3 → CDEK numeric currency code
CDEK_CURRENCY_CODE_MAP: dict[str, int] = {
    "RUB": CDEK_CURRENCY_RUB,
    "KZT": CDEK_CURRENCY_KZT,
    "USD": CDEK_CURRENCY_USD,
    "EUR": CDEK_CURRENCY_EUR,
    "GBP": CDEK_CURRENCY_GBP,
    "CNY": CDEK_CURRENCY_CNY,
    "BYN": CDEK_CURRENCY_BYN,
    "UAH": CDEK_CURRENCY_UAH,
    "KGS": CDEK_CURRENCY_KGS,
    "AMD": CDEK_CURRENCY_AMD,
    "TRY": CDEK_CURRENCY_TRY,
    "THB": CDEK_CURRENCY_THB,
    "KRW": CDEK_CURRENCY_KRW,
    "AED": CDEK_CURRENCY_AED,
    "UZS": CDEK_CURRENCY_UZS,
    "MNT": CDEK_CURRENCY_MNT,
    "PLN": CDEK_CURRENCY_PLN,
    "AZN": CDEK_CURRENCY_AZN,
    "GEL": CDEK_CURRENCY_GEL,
    "JPY": CDEK_CURRENCY_JPY,
    "VND": CDEK_CURRENCY_VND,
}

# CDEK numeric currency code → ISO 4217 alpha-3 (reverse of the map
# above). Used to label calculator results in their actual currency
# instead of hard-coding RUB.
CDEK_NUMERIC_TO_ISO_CURRENCY: dict[int, str] = {
    numeric: iso for iso, numeric in CDEK_CURRENCY_CODE_MAP.items()
}

# Default destination-country → CDEK currency mapping for rate calculation
# (used when the caller doesn't supply an explicit currency).
CDEK_DEFAULT_CURRENCY_BY_COUNTRY: dict[str, int] = {
    "RU": CDEK_CURRENCY_RUB,
    "KZ": CDEK_CURRENCY_KZT,
    "BY": CDEK_CURRENCY_BYN,
    "UA": CDEK_CURRENCY_UAH,
    "KG": CDEK_CURRENCY_KGS,
    "AM": CDEK_CURRENCY_AMD,
    "UZ": CDEK_CURRENCY_UZS,
    "AZ": CDEK_CURRENCY_AZN,
    "GE": CDEK_CURRENCY_GEL,
    "TR": CDEK_CURRENCY_TRY,
    "CN": CDEK_CURRENCY_CNY,
    "MN": CDEK_CURRENCY_MNT,
}


def cdek_currency_for(
    currency_code: str | None, destination_country: str | None
) -> int:
    """Resolve CDEK numeric currency code from ISO 4217 or destination country.

    Resolution order:
    1. Explicit ``currency_code`` (e.g. ``"KZT"``) if it maps to a known CDEK code.
    2. Default for ``destination_country`` (e.g. ``"KZ"`` → KZT).
    3. ``CDEK_CURRENCY_RUB`` as a safe fallback.
    """
    if currency_code:
        code = CDEK_CURRENCY_CODE_MAP.get(currency_code.upper())
        if code is not None:
            return code
    if destination_country:
        code = CDEK_DEFAULT_CURRENCY_BY_COUNTRY.get(destination_country.upper())
        if code is not None:
            return code
    return CDEK_CURRENCY_RUB


def cdek_currency_to_iso(
    numeric_code: int | str | None,
    *,
    fallback: str = "RUB",
) -> str:
    """Map a CDEK numeric currency code back to an ISO 4217 alpha-3 string.

    The calculator response echoes the currency it priced in as a CDEK
    numeric code (Приложение 14). ``parse_tariff_list_response`` uses
    this to label every quote in its real currency instead of assuming
    RUB. Unknown / missing codes fall back to ``fallback`` (RUB).
    """
    if numeric_code is None:
        return fallback
    try:
        numeric = int(numeric_code)
    except TypeError, ValueError:
        return fallback
    return CDEK_NUMERIC_TO_ISO_CURRENCY.get(numeric, fallback)


# ---------------------------------------------------------------------------
# CDEK delivery-failure reason codes
# ---------------------------------------------------------------------------
# Приложение 2 — дополнительные статусы заказов. Carried on a status as
# ``reason_code`` and explains *why* an order is NOT_DELIVERED / being
# returned. Surfaced into ``TrackingEvent.description`` so operators see
# the cause without decoding integers.

CDEK_REASON_CODE_MAP: dict[str, str] = {
    "1": "Возврат: неверный адрес",
    "2": "Возврат: не дозвонились",
    "3": "Возврат: адресат не проживает",
    "4": "Возврат: вес отличается от заявленного",
    "5": "Возврат: фактически нет отправления",
    "6": "Возврат: дубль номера заказа",
    "7": "Возврат: не доставляем в данный город/регион",
    "8": "Возврат: повреждение упаковки при приёмке от отправителя",
    "9": "Возврат: повреждение упаковки у перевозчика",
    "10": "Возврат: повреждение упаковки на складе/у курьера",
    "11": "Отказ от получения: без объяснения",
    "12": "Отказ от получения: претензия к качеству товара",
    "13": "Отказ от получения: недовложение",
    "14": "Отказ от получения: пересорт",
    "15": "Отказ от получения: не устроили сроки",
    "16": "Отказ от получения: уже купил",
    "17": "Отказ от получения: передумал",
    "18": "Отказ от получения: ошибка оформления",
    "19": "Отказ от получения: повреждение упаковки у получателя",
    "20": "Частичная доставка",
    "21": "Отказ от получения: нет денег",
    "22": "Отказ от получения: товар не подошёл/не понравился",
    "23": "Возврат: истёк срок хранения",
    "24": "Возврат: не прошёл таможню",
    "25": "Возврат: является коммерческим грузом",
    "26": "Утерян",
    "27": "Не востребован, утилизация",
    "31": "Возврат по запросу отправителя",
    "32": "Возврат по запросу плательщика",
    "33": "СНТ не получено, возврат отправителю",
    "34": "CDEK Shopping: истёк срок хранения",
}

# Приложение 3 — причины проблем доставки. Carried by the DELIV_PROBLEM
# webhook as ``code``; surfaced into the synthetic problem TrackingEvent.
CDEK_DELIVERY_PROBLEM_MAP: dict[str, str] = {
    "1": "Телефон неверный",
    "9": "Груз не готов",
    "11": "Отказ от оплаты",
    "13": "Контактное лицо отсутствует",
    "17": "Организация не работает",
    "19": "Смена адреса",
    "35": "Не успеваю",
    "36": "Самозабор",
    "37": "Постамат переполнен",
    "38": "Постамат не работает",
    "39": "Груз не влез в ячейку постамата",
    "40": "Отказ от получения",
    "41": "Отказ от заявки",
    "42": "Требуется пропуск",
    "43": "Платный въезд",
    "44": "Закрытая территория",
    "45": "Нет документа, удостоверяющего личность",
    "46": "Смена города",
    "47": "Адрес не существует",
    "48": "Доставка в А/Я",
    "49": "Опасный груз",
    "52": "Отказ с адреса",
    "53": "Изменение интервала по согласованию с клиентом",
    "54": "Постаматное приложение не работает",
    "55": "Груз не найден",
    "56": "Передача на ПВЗ",
    "57": "Не могу доставить на ПВЗ",
}


def cdek_reason_code_label(reason_code: str | int | None) -> str | None:
    """Return the human-readable label for a CDEK ``reason_code``.

    Returns ``None`` for missing / unknown codes so callers can decide
    whether to fall back to the raw value.
    """
    if reason_code is None or reason_code == "":
        return None
    return CDEK_REASON_CODE_MAP.get(str(reason_code))


def cdek_delivery_problem_label(problem_code: str | int | None) -> str | None:
    """Return the human-readable label for a CDEK delivery-problem code."""
    if problem_code is None or problem_code == "":
        return None
    return CDEK_DELIVERY_PROBLEM_MAP.get(str(problem_code))


# ---------------------------------------------------------------------------
# CDEK print form types
# ---------------------------------------------------------------------------

CDEK_PRINT_WAYBILL = "waybill"
CDEK_PRINT_BARCODE = "barcode"
