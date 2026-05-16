/**
 * Checkout-domen statik URL'lar / havolalari (CHK-021). DRY: sheet
 * "Подробнее" / "Узнать ИНН" tugmalari shu yerdan o'qiydi.
 */

export const CUSTOMS_INFO_URL = 'https://teletype.in/@loyaltymarket/customs-info';

export const INN_LOOKUP_URL = 'https://lk.nalog.ru/inn';

/**
 * CHK-021 H: CIS passport formatlari (frontend dictionary).
 *
 * **HOZIR:** Backend faqat RF passport qabul qiladi (`CreateRecipientRequest`
 * pattern). CIS passport validation backend tomon ham talab — BACK-LOG-002
 * alohida ticketda kuzatiladi. Bu yerda dictionary tayyor, kelajakda
 * `validateCustomsStrict` country-aware bo'lganda faollashtiriladi.
 *
 * `number: 0` — qisqartirilgan format (ID number, alphanumeric).
 */
export const PASSPORT_FORMATS = Object.freeze({
  RU: { series: 4, number: 6, label: 'Серия и номер паспорта РФ' },
  UZ: { series: 2, number: 7, label: 'Серия и номер паспорта Узбекистана' },
  KZ: { series: 9, number: 0, label: 'ИИН Казахстана' },
  BY: { series: 4, number: 7, label: 'Серия и номер паспорта Беларуси' },
  UA: { series: 2, number: 6, label: 'Серия и номер паспорта Украины' },
});
