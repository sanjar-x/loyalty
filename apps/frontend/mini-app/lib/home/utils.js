/**
 * Bosh sahifa (`app/page.jsx`) pure yordamchilari — audit #1 (god-komponentlar
 * dekompozitsiyasi) doirasida inline'dan ajratildi. DOM/state'siz, oson test.
 */

/** Matnni qidiruv/solishtirish uchun normalizatsiya: trim + bo'shliqlarni
 *  bittaga + lowercase. */
export function normalizeSearchText(value) {
  return String(value || '')
    .trim()
    .replace(/\s+/g, ' ')
    .toLowerCase();
}

/** Narx string'idan (`"1 599 ₽"`) butun son ajratib oladi. Yaroqsiz → 0. */
export function priceToNumber(value) {
  const n = Number(String(value || '').replace(/[^0-9]/g, ''));
  return Number.isFinite(n) ? n : 0;
}
