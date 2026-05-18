/**
 * Quote error message resolver (CHK-017).
 *
 * Backend `/logistics/rates/quote` on provider-side 5xx returns various
 * technical details (`Provider 'X' has no default_origin configured`,
 * `gateway timeout`, ...). For the UI we render a short user-friendly text:
 *  • if `default_origin` is found — "operator temporarily unavailable"
 *  • otherwise — generic provider unavailable
 *
 * Pure: reads the backend message string and returns UI text. Full i18n
 * is a separate ticket — for now string-match suffices (single locale: ru-RU).
 *
 * @param {string | null | undefined} backendMessage
 * @returns {string}
 */
const FALLBACK = 'Сервис доставки временно недоступен — выберите другой ПВЗ';
const MISSING_ORIGIN = 'Доставка этим оператором временно недоступна. Выберите другой ПВЗ.';

export function pickProviderErrorMessage(backendMessage) {
  if (typeof backendMessage !== 'string' || !backendMessage) return FALLBACK;
  if (backendMessage.includes('default_origin')) return MISSING_ORIGIN;
  return FALLBACK;
}

export const PROVIDER_ERROR_FALLBACK = FALLBACK;
export const PROVIDER_ERROR_MISSING_ORIGIN = MISSING_ORIGIN;
