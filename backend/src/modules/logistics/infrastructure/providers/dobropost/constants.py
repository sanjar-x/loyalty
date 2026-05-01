"""
DobroPost API constants — endpoints, token TTL, status taxonomy.

Maps DobroPost ``status_id`` (Integer) to unified ``TrackingStatus``
domain enum. Source — ``docs/dobropost_shipment_api/status-codes.md``
(40 status_id codes in 4 logical groups).
"""

from src.modules.logistics.domain.value_objects import TrackingStatus

# ---------------------------------------------------------------------------
# DobroPost API URLs
# ---------------------------------------------------------------------------

DOBROPOST_PRODUCTION_URL = "https://api.dobropost.com"
DOBROPOST_SIGN_IN_PATH = "/api/shipment/sign-in"
DOBROPOST_SHIPMENT_PATH = "/api/shipment"

# Token TTL fixed by DobroPost (no expires_in in response). 12 hours per
# reference.md §1. We refresh 5 min early to absorb clock skew.
DOBROPOST_TOKEN_TTL_SECONDS = 12 * 60 * 60
DOBROPOST_TOKEN_REFRESH_BUFFER_SECONDS = 5 * 60

# ---------------------------------------------------------------------------
# DobroPost status_id → unified TrackingStatus
# ---------------------------------------------------------------------------
# Full enumeration mirrors docs/dobropost_shipment_api/status-codes.md.
# Keys are *string* representations because the webhook delivers status as
# text and we normalise to ``str(status_id)`` before lookup.

DOBROPOST_STATUS_MAP: dict[str, TrackingStatus] = {
    # ---- Базовая логистическая цепочка (1-9) ----
    "1": TrackingStatus.CREATED,  # Ожидается на складе
    "2": TrackingStatus.ACCEPTED,  # Получен от курьера
    "3": TrackingStatus.IN_TRANSIT,  # Обработан на складе
    "4": TrackingStatus.IN_TRANSIT,  # Добавлен в мешок
    "5": TrackingStatus.IN_TRANSIT,  # Добавлен в реестр
    "6": TrackingStatus.IN_TRANSIT,  # Покинул склад в Китае
    "7": TrackingStatus.CUSTOMS,  # Поступил на таможню в Китае
    "8": TrackingStatus.CUSTOMS,  # Поступил на таможню в России
    "9": TrackingStatus.IN_TRANSIT,  # Передан партнёру (промежуточный)
    # ---- Таможенное оформление — informational / requires action ----
    "500": TrackingStatus.CUSTOMS,
    "510": TrackingStatus.CUSTOMS,
    "520": TrackingStatus.IN_TRANSIT,
    "521": TrackingStatus.IN_TRANSIT,
    "530": TrackingStatus.IN_TRANSIT,
    "531": TrackingStatus.CUSTOMS,
    "532": TrackingStatus.IN_TRANSIT,
    "540": TrackingStatus.CUSTOMS,
    "570": TrackingStatus.CUSTOMS,
    "591": TrackingStatus.CUSTOMS,
    # ---- Cross-border arrival trigger ----
    "648": TrackingStatus.IN_TRANSIT,  # Подготовлено к отгрузке last mile
    "649": TrackingStatus.IN_TRANSIT,  # Покинула таможню → передана на доставку по РФ
    # ---- Terminal failures ----
    "541": TrackingStatus.EXCEPTION,  # Признана коммерческой
    "542": TrackingStatus.EXCEPTION,  # Отсутствуют документы
    "543": TrackingStatus.EXCEPTION,  # Некорректное заполнение
    "544": TrackingStatus.EXCEPTION,  # Нет корректных паспортных данных
    "545": TrackingStatus.EXCEPTION,  # Паспорт не в реестре
    "546": TrackingStatus.EXCEPTION,  # Прочие
    "600": TrackingStatus.LOST,  # Посылка не пришла
    # ---- Развёрнутые отказы с кодами ----
    "590204": TrackingStatus.EXCEPTION,
    "590401": TrackingStatus.EXCEPTION,
    "590404": TrackingStatus.EXCEPTION,
    "590405": TrackingStatus.EXCEPTION,
    "590409": TrackingStatus.EXCEPTION,
    "590410": TrackingStatus.EXCEPTION,
    "590413": TrackingStatus.EXCEPTION,
    "590420": TrackingStatus.EXCEPTION,
    "590592": TrackingStatus.EXCEPTION,
    # ---- Редактирование данных посылки (270-272): не маппим ----
    # Не вызывают FSM-transition; адаптер пропускает их через _UNMAPPED_STATUSES.
}

# Status_ids that are *informational only* — adapter skips them rather
# than producing a TrackingEvent with EXCEPTION fallback. Currently the
# "edit shipment" group (270-272).
DOBROPOST_INFO_ONLY_STATUS_IDS: frozenset[str] = frozenset({"270", "271", "272"})

# Human-readable Russian names → status_id, used to resolve the textual
# ``status`` field in webhook payload format №2 back to a numeric code.
# Order matters only for collisions ("Выпуск товаров..." appears 4×): we
# keep the lowest id for the canonical mapping; specific id is preserved
# in ``provider_status_code`` only when DobroPost sends ``status_id``
# directly (poll path).
DOBROPOST_NAME_TO_STATUS_ID: dict[str, str] = {
    "Ожидается на складе": "1",
    "Получен от курьера": "2",
    "Обработан на складе": "3",
    "Добавлен в мешок": "4",
    "Добавлен в реестр": "5",
    "Покинул склад в Китае": "6",
    "Поступил на таможню в Китае": "7",
    "Поступил на таможню в России": "8",
    "Передан партнеру": "9",
    "Запрос на редактирование данных посылки": "270",
    "Запрос на редактирование данных посылки отклонен": "271",
    "Произведено редактирование данных посылки": "272",
    "Начало таможенного оформления": "500",
    "Требуется уплатить таможенные пошлины": "510",
    "Выпуск товаров без уплаты таможенных платежей": "520",
    "Выпуск товаров (таможенные платежи уплачены)": "530",
    "Ожидание обязательной оплаты таможенной пошлины": "540",
    "Подготовлено к отгрузке в доставку последней мили": "648",
    "Покинула таможню и передана на доставку по РФ": "649",
    "Посылка не пришла": "600",
    "Продление времени обработки": "570",
}


def dobropost_status_to_tracking(status_id: str) -> TrackingStatus:
    """Map a DobroPost status_id (as string) to unified TrackingStatus.

    Falls back to ``EXCEPTION`` for unknown codes. Information-only
    statuses (270-272) are NOT routed through here — adapter checks
    ``DOBROPOST_INFO_ONLY_STATUS_IDS`` first.
    """
    return DOBROPOST_STATUS_MAP.get(status_id, TrackingStatus.EXCEPTION)


def dobropost_name_to_status_id(name: str) -> str | None:
    """Resolve textual status from webhook payload to canonical status_id.

    Returns ``None`` on miss — adapter then sets ``provider_status_code
    = "unknown"`` and logs a warning so the dictionary can be extended.
    """
    return DOBROPOST_NAME_TO_STATUS_ID.get(name.strip())
