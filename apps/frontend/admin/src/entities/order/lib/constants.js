// 14-state Order FSM (raw backend status). Backend currently exports it as
// an unconstrained string in OpenAPI; this mirror lives on the frontend so
// pills/labels stay in one place. Any drift from the backend domain enum
// must be reconciled here — preferably by swapping to a backend-exported
// enum once that lands.
export const ORDER_STATUSES = [
  'pending',
  'paid',
  'procured',
  'on_hold',
  'arrived_in_ru',
  'in_last_mile',
  'ready_for_pickup',
  'delivered',
  'returning',
  'returned',
  'cancelled',
  'refunding',
  'refunded',
  'expired',
];

// Russian admin labels for raw FSM states. Used in the order detail badge,
// the FSM history table and the status filter chips.
export const ORDER_STATUS_LABELS = {
  pending: 'Ожидает оплаты',
  paid: 'Оплачен',
  procured: 'В закупке',
  on_hold: 'На паузе',
  arrived_in_ru: 'Прибыл в РФ',
  in_last_mile: 'Last-mile доставка',
  ready_for_pickup: 'Готов к выдаче',
  delivered: 'Получен',
  returning: 'Возвращается',
  returned: 'Возвращён',
  cancelled: 'Отменён',
  refunding: 'Возврат средств',
  refunded: 'Средства возвращены',
  expired: 'Истёк',
};

// Customer-facing status copy. Backend is the source of truth — these labels
// only render the string the BE sends in `customerFacingStatus`. The mapping
// is here so the same translation works in pills + filter chips when the BE
// emits one of the well-known buckets.
export const CUSTOMER_FACING_STATUS_LABELS = {
  awaiting_payment: 'Ожидает оплаты',
  in_processing: 'В обработке',
  on_pause: 'На паузе',
  in_transit: 'В пути',
  ready_for_pickup: 'Готов к выдаче',
  received: 'Получен',
  cancelled: 'Отменён',
  refunded: 'Возврат',
};

// Whitelist of statuses exposed in the list filter. Some terminal states
// (refunding/refunded/returning) are folded into a single "Завершённые"
// segment to keep the tab bar readable; we show those via "Архив".
export const ORDER_STATUS_FILTER_GROUPS = [
  { key: 'all', label: 'Все', statuses: null },
  { key: 'pending', label: 'Ожидает оплаты', statuses: ['pending'] },
  { key: 'paid', label: 'Оплаченные', statuses: ['paid'] },
  { key: 'procured', label: 'В закупке', statuses: ['procured'] },
  { key: 'on_hold', label: 'На паузе', statuses: ['on_hold'] },
  {
    key: 'in_transit',
    label: 'В пути',
    statuses: ['arrived_in_ru', 'in_last_mile'],
  },
  {
    key: 'ready_for_pickup',
    label: 'К выдаче',
    statuses: ['ready_for_pickup'],
  },
  { key: 'delivered', label: 'Полученные', statuses: ['delivered'] },
  {
    key: 'archive',
    label: 'Архив',
    statuses: [
      'cancelled',
      'expired',
      'returning',
      'returned',
      'refunding',
      'refunded',
    ],
  },
];

// Conditional-button gates per task spec. Lifted to a shared module so the
// detail page header and any future bulk-action surface read from one place.
export const ACTION_GATES = {
  procure: ['paid'],
  hold: ['paid', 'procured', 'arrived_in_ru', 'in_last_mile'],
  resume: ['on_hold'],
  forceCancel: ['pending', 'paid', 'procured', 'on_hold'],
  changePickup: ['pending', 'paid', 'procured', 'arrived_in_ru'],
};

export function canPerformAction(action, status) {
  const gate = ACTION_GATES[action];
  return Array.isArray(gate) && gate.includes(status);
}

// ---------------------------------------------------------------------------
// HoldReason / CancelReason — typed enums (post-D0.1)
// ---------------------------------------------------------------------------
// `HOLD_REASON_MAX` / `CANCEL_REASON_MAX` are the BFF-side string-length
// caps for the legacy free-form path; with the typed enum every value is
// well under the limit, but the constants stay so the BFF guard can keep
// rejecting accidentally-oversized payloads.
export const HOLD_REASON_MAX = 32;
export const CANCEL_REASON_MAX = 64;

// `HoldReason` enum mirrors `backend.json` 1:1. Treat as the single
// source of truth for both the modal picker and any future status-pill
// label that needs to render an existing hold (`order.holdReason`).
export const HOLD_REASON_VALUES = [
  'passport_invalid',
  'customs_rejected',
  'stuck_in_cn',
  'manual_review',
  'booking_failed',
];

// Subset that the admin can pick **manually** in the HoldResumeModal.
// `booking_failed` is reserved for the system path (D1.2 retry/hold
// pipeline writes it on procurement failure) — exposing it as a
// quick-pick would let an admin spoof the booking-pending UX banner.
export const HOLD_REASONS_FOR_ADMIN = HOLD_REASON_VALUES.filter(
  (r) => r !== 'booking_failed',
);

export const HOLD_REASON_LABELS = {
  passport_invalid: 'Паспорт не прошёл валидацию',
  customs_rejected: 'Отклонено таможней',
  stuck_in_cn: 'Застряло на китайской стороне',
  manual_review: 'Ручная проверка',
  booking_failed: 'Сбой бронирования логистики',
};

// `CancellationReason` enum mirrors `backend.json` 1:1. The grouped
// taxonomy is fetched at runtime from the backend's `_meta/cancellation-
// reasons` endpoint (BFF exposes it as `/api/admin/orders/meta/
// cancellation-reasons`) so the UI can render group buckets without
// hard-coding the partition (backend may rebalance categories without
// bumping the API version). These labels stay client-side because the
// backend response is language-agnostic — frontend i18n responsibility
// only.
export const CANCELLATION_REASON_LABELS = {
  // customer
  customer_changed_mind: 'Передумал',
  customer_found_better_price: 'Нашёл цену дешевле',
  customer_wrong_item: 'Заказал не то',
  customer_delivery_too_slow: 'Слишком долгая доставка',
  customer_duplicate_order: 'Дубль заказа',
  // merchant
  merchant_out_of_stock: 'Нет в наличии',
  merchant_price_error: 'Ошибка в цене',
  merchant_fraud_suspected: 'Подозрение на мошенничество',
  merchant_region_not_served: 'Не доставляем в регион',
  merchant_item_discontinued: 'Товар снят с продажи',
  merchant_force_cancel: 'Принудительная отмена со стороны продавца',
  // system
  system_payment_failed: 'Ошибка оплаты',
  system_payment_timeout: 'Истекло время оплаты',
  system_auth_expired: 'Истекла авторизация',
  system_hold_ttl_expired: 'Истёк TTL hold-а',
  // logistics
  logistics_customs_rejected: 'Отклонено таможней',
  logistics_lost_in_transit: 'Потеряно в пути',
  logistics_undeliverable_address: 'Адрес недоставляем',
  logistics_passport_invalid: 'Паспорт не прошёл валидацию (логистика)',
};

export const CANCELLATION_CATEGORY_LABELS = {
  customer: 'От покупателя',
  merchant: 'От продавца',
  system: 'Системное',
  logistics: 'Логистическое',
};

export function cancellationReasonLabel(code) {
  return CANCELLATION_REASON_LABELS[code] ?? code;
}

export function holdReasonLabel(code) {
  return HOLD_REASON_LABELS[code] ?? code;
}

// ---------------------------------------------------------------------------
// Legacy filter taxonomy — kept to keep `entities/order/index.js` callers
// (existing OrdersList / ReasonFilters) compiling while we refactor against
// the real backend. Safe to retire once the order-filter slice moves off the
// mock-driven UI.
// ---------------------------------------------------------------------------

export const STATUS_LABELS = {
  placed: 'Оформленные',
  in_transit: 'В пути',
  pickup_point: 'В пункте выдачи',
  canceled: 'Отмененные',
  received: 'Полученные',
};

export const STATUS_PILL_LABELS = {
  placed: 'Оформлен',
  in_transit: 'В пути',
  pickup_point: 'Готов к выдаче',
  canceled: 'Отменен',
  received: 'Получен',
};

export const REASON_FILTERS = [
  'not_for_sale',
  'release_refusal',
  'storage_expired',
];

export const REASON_FILTER_LABELS = {
  not_for_sale: 'Нет в продаже',
  release_refusal: 'Отказ в выпуске посылки',
  storage_expired: 'Срок хранения истёк',
};
