/**
 * Backend qo'llab-quvvatlaydigan PVZ provider'lari — `openapi.json`dagi
 * `LogisticsProviderCodeEnum`. (Boxberry, Pochta Rossii hozircha
 * qo'llab-quvvatlanmaydi.) Audit #1: `app/checkout/pickup/page.jsx`'dan
 * ajratildi.
 */
export const PVZ_PROVIDERS = [
  { code: 'cdek', label: 'CDEK', short: 'CDEK' },
  { code: 'yandex_delivery', label: 'Яндекс Доставка', short: 'Яндекс' },
];

export const PVZ_PROVIDER_CODES = PVZ_PROVIDERS.map((p) => p.code);
