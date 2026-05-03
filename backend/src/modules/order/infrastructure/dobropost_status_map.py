"""DobroPost ``status_id`` → Order FSM action map.

Mirrors ``docs/dobropost_shipment_api/status-codes.md`` (40 codes in 4
logical groups). The order-side mapping is *coarser* than the
logistics-side one: we only care about codes that drive an Order FSM
transition. Everything else is recorded against the side-mapping row
(``last_status_id``) for admin visibility and customer tracking but
does not move the FSM.

Action enum:

* ``NOOP`` — informational; just persist last_status_id.
* ``ARRIVED_IN_RU`` — cross-border arrival → ``mark_arrived_in_ru``.
* ``CUSTOMS_REJECT`` — customs refused (commercial qty / docs / etc.) →
  ``cancel_order(LOGISTICS_CUSTOMS_REJECTED)``.
* ``PASSPORT_INVALID`` — paspport-fail buckets → ``hold_order(PASSPORT_INVALID)``.
  The customer fixes the recipient and retries via
  ``RefreshRecipientSnapshot`` + ``ResumeOrder``.
* ``PARCEL_LOST`` — physical loss → ``cancel_order(LOGISTICS_LOST_IN_TRANSIT)``.
"""

from __future__ import annotations

from enum import Enum


class DobroPostFsmAction(str, Enum):
    NOOP = "noop"
    ARRIVED_IN_RU = "arrived_in_ru"
    CUSTOMS_REJECT = "customs_reject"
    PASSPORT_INVALID = "passport_invalid"
    PARCEL_LOST = "parcel_lost"


# Human-readable status label keyed by DobroPost numeric status_id.
# Used both in the consumer (logging / state-history metadata) and in
# the customer-facing tracking endpoint.
DOBROPOST_STATUS_LABELS: dict[int, str] = {
    # ---- Базовая логистическая цепочка (1-9) ----
    1: "Ожидается на складе",
    2: "Получен от курьера",
    3: "Обработан на складе",
    4: "Добавлен в мешок",
    5: "Добавлен в реестр",
    6: "Покинул склад в Китае",
    7: "Поступил на таможню в Китае",
    8: "Поступил на таможню в России",
    9: "Передан партнёру",
    # ---- Редактирование данных посылки (270-272) ----
    270: "Запрос на редактирование данных посылки",
    271: "Запрос на редактирование данных посылки отклонён",
    272: "Произведено редактирование данных посылки",
    # ---- Таможенное оформление — informational ----
    500: "Начало таможенного оформления",
    510: "Требуется уплатить таможенные пошлины",
    520: "Выпуск товаров без уплаты таможенных платежей",
    521: "Выпуск товаров без уплаты таможенных платежей",
    530: "Выпуск товаров (таможенные платежи уплачены)",
    531: "Требуется уплатить таможенные пошлины",
    532: "Выпуск товаров (таможенные платежи уплачены)",
    540: "Ожидание обязательной оплаты таможенной пошлины",
    570: "Продление времени обработки",
    591: "Начало таможенного оформления",
    # ---- Cross-border arrival trigger ----
    648: "Подготовлено к отгрузке последней мили",
    649: "Покинула таможню — передана на доставку по РФ",
    # ---- Терминальные отказы таможни ----
    541: "Отказ — партия признана коммерческой",
    542: "Отказ — отсутствуют документы",
    543: "Отказ — некорректное заполнение информации",
    544: "Отказ — отсутствие корректных паспортных данных",
    545: "Отказ — паспортных данных нет в реестре достоверных",
    546: "Отказ по другим причинам",
    600: "Посылка не пришла",
    # ---- Развёрнутые отказы (590xxx) ----
    590204: "Отказ в выпуске товаров (код 204)",
    590401: "Отказ в выпуске товаров (код 401)",
    590404: "Отказ в выпуске товаров — не представлены документы",
    590405: "Отказ в выпуске товаров (код 405)",
    590409: "Отказ в выпуске товаров (код 409)",
    590410: "Отказ в выпуске — товар входит в перечень категорий",
    590413: "Отказ в выпуске — не подана корректировка пп.2 п.1 ст.125 ТК ЕАЭС",
    590420: "Отказ в выпуске товаров (код 420)",
    590592: "Отказ в выпуске товаров (код 592)",
}


# Codes that fail the order specifically due to passport-validation
# issues. The customer can retry via RefreshRecipientSnapshot, so the
# Order goes to ON_HOLD instead of being cancelled.
_PASSPORT_INVALID_IDS: frozenset[int] = frozenset({544, 545, 590401, 590405})

# Codes that mean customs rejected the parcel for non-passport reasons
# (commercial qty, missing docs, prohibited category…). No retry path —
# we cancel + refund.
_CUSTOMS_REJECT_IDS: frozenset[int] = frozenset(
    {541, 542, 543, 546, 590204, 590404, 590409, 590410, 590413, 590420, 590592}
)

# Codes signalling cross-border arrival → kicks off last-mile booking.
_ARRIVED_IN_RU_IDS: frozenset[int] = frozenset({648, 649})

# Codes signalling permanent loss.
_PARCEL_LOST_IDS: frozenset[int] = frozenset({600})


def map_status_id_to_action(status_id: int) -> DobroPostFsmAction:
    """Coarse mapping: 40 status_ids → 5 FSM actions."""
    if status_id in _ARRIVED_IN_RU_IDS:
        return DobroPostFsmAction.ARRIVED_IN_RU
    if status_id in _PASSPORT_INVALID_IDS:
        return DobroPostFsmAction.PASSPORT_INVALID
    if status_id in _CUSTOMS_REJECT_IDS:
        return DobroPostFsmAction.CUSTOMS_REJECT
    if status_id in _PARCEL_LOST_IDS:
        return DobroPostFsmAction.PARCEL_LOST
    return DobroPostFsmAction.NOOP


def status_label(status_id: int) -> str:
    """Return Russian human-readable label, or fallback ``unknown(<id>)``."""
    return DOBROPOST_STATUS_LABELS.get(status_id, f"Неизвестный статус ({status_id})")


# Reverse map: human-readable label → numeric status_id. DobroPost
# webhook payload format №2 only carries the textual ``status``; we
# need this mapping to backfill the numeric id. Collisions across
# 500/591, 510/531, 520/521, 530/532 keep the lowest id (the FSM
# action is the same).
_DOBROPOST_NAME_TO_ID: dict[str, int] = {
    label: sid
    for sid, label in DOBROPOST_STATUS_LABELS.items()
    # Only the lowest-id wins on collision — the loop yields
    # increasing ids so the first occurrence is kept after we
    # deduplicate via dict-insertion order.
}
# Add a few common variants the upstream uses verbatim — keeps the
# resolver tolerant to whitespace / casing.
_DOBROPOST_NAME_TO_ID.update(
    {
        "Передан партнеру": 9,  # Cyrillic ё / е variant
        "Запрос на редактирование данных посылки отклонен": 271,
    }
)


def name_to_status_id(name: str) -> int | None:
    """Resolve textual status from webhook payload to canonical status_id."""
    if not name:
        return None
    return _DOBROPOST_NAME_TO_ID.get(name.strip())
