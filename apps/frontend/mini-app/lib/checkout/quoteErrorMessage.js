/**
 * Quote error message resolver (CHK-017).
 *
 * Backend `/logistics/rates/quote` provider-side 5xx'da har xil technical
 * detail qaytaradi (`Provider 'X' has no default_origin configured`,
 * `gateway timeout`, ...). UI uchun foydalanuvchiga mos qisqa matn:
 *  • `default_origin` topilsa — "operator vaqtincha mavjud emas"
 *  • aks holda — generic provider unavailable
 *
 * Pure: backend message string'ini o'qib UI matni qaytaradi. To'liq i18n
 * alohida ticketda — hozircha string-match yetadi (bitta lokal: ru-RU).
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
