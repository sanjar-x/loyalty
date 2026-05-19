// Walk-in order constants. Kept narrow to the feature; values that escape
// (e.g. payment methods rendered elsewhere) are re-exported via the
// feature barrel.

// Walk-in customers settle in store, so RUB is the only currency the
// admin form ever submits. Multi-currency walk-in would need a SKU
// currency selector + currencyMismatch validation, which is explicitly
// out of scope for the MVP (see SPEC § "Out of scope").
export const DEFAULT_CURRENCY = 'RUB';

// Mirrors backend `Settings.WALK_IN_MAX_PRICE_OVERRIDE_RATIO`. Hard-coded
// here as a known shortcut — when the backend exposes admin config via
// `/api/v1/admin/config` this should be fetched on form mount instead so
// a server-side ratio change doesn't require a frontend redeploy.
//
// TODO(walk-in): replace with /admin/config fetch once that endpoint
// ships. Tracked as separate ticket — see SPEC decisions section.
export const MAX_PRICE_OVERRIDE_RATIO = 10;

// One per backend `OfflinePaymentMethod`. The label is the Russian UI
// string shown in the method dropdown; `referenceHint` is rendered as
// helper text under the reference field so the admin knows what to put
// in (per SPEC § "Reference recommendations").
export const OFFLINE_PAYMENT_METHODS = [
  {
    value: 'cash',
    label: 'Наличные',
    referenceHint: 'Номер кассового чека или POS-<timestamp>',
  },
  {
    value: 'bank_transfer',
    label: 'Банковский перевод',
    referenceHint: 'Номер выписки или referenceID банка',
  },
  {
    value: 'card_terminal',
    label: 'Терминал',
    referenceHint: 'ID транзакции терминала',
  },
  {
    value: 'other',
    label: 'Другое',
    referenceHint: 'Свободное описание основания платежа',
  },
];

// Pickup carriers the walk-in form supports. Matches
// `features/order-actions/ui/ChangePickupPointModal` so the search UX
// stays consistent. SPEC originally listed four carriers
// (cdek/yandex/boxberry/pochta); only the two below are actually wired
// on the backend today — adding more requires both backend enum + a
// pickup-point provider integration.
export const PICKUP_CARRIERS = [
  { code: 'cdek', label: 'СДЭК' },
  { code: 'yandex_delivery', label: 'Яндекс.Доставка' },
];
