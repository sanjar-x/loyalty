/**
 * Static URLs / references for the checkout domain (CHK-021). DRY: sheet
 * "Details" / "Look up INN" buttons read from here.
 */

export const CUSTOMS_INFO_URL = 'https://teletype.in/@loyaltymarket/customs-info';

export const INN_LOOKUP_URL = 'https://lk.nalog.ru/inn';

/**
 * CHK-021 H: CIS passport formats (frontend dictionary).
 *
 * **CURRENTLY:** Backend only accepts an RF passport (`CreateRecipientRequest`
 * pattern). CIS passport validation is also required on the backend side —
 * tracked separately in BACK-LOG-002. The dictionary is ready here and will
 * be activated in the future when `validateCustomsStrict` becomes
 * country-aware.
 *
 * `number: 0` — shortened format (ID number, alphanumeric).
 */
export const PASSPORT_FORMATS = Object.freeze({
  RU: { series: 4, number: 6, label: 'Серия и номер паспорта РФ' },
  UZ: { series: 2, number: 7, label: 'Серия и номер паспорта Узбекистана' },
  KZ: { series: 9, number: 0, label: 'ИИН Казахстана' },
  BY: { series: 4, number: 7, label: 'Серия и номер паспорта Беларуси' },
  UA: { series: 2, number: 6, label: 'Серия и номер паспорта Украины' },
});
