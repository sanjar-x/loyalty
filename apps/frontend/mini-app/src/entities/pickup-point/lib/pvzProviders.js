/**
 * Backend-supported PVZ providers — `LogisticsProviderCodeEnum` from
 * `openapi.json`. (Boxberry and Pochta Rossii are not yet supported.)
 * Audit #1: extracted from `app/checkout/pickup/page.jsx`.
 */
export const PVZ_PROVIDERS = [
  { code: 'cdek', label: 'CDEK', short: 'CDEK' },
  { code: 'yandex_delivery', label: 'Яндекс Доставка', short: 'Яндекс' },
];

export const PVZ_PROVIDER_CODES = PVZ_PROVIDERS.map((p) => p.code);
