/**
 * Pure helpers for the home page (`app/page.jsx`) — extracted from inline
 * under audit #1 (god-component decomposition). No DOM/state, easy to test.
 */

/** Normalize text for search/comparison: trim + collapse whitespace to one
 *  space + lowercase. */
export function normalizeSearchText(value) {
  return String(value || '')
    .trim()
    .replace(/\s+/g, ' ')
    .toLowerCase();
}

/** Extract an integer from a price string (`"1 599 ₽"`). Invalid → 0. */
export function priceToNumber(value) {
  const n = Number(String(value || '').replace(/[^0-9]/g, ''));
  return Number.isFinite(n) ? n : 0;
}
