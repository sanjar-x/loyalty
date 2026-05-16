/**
 * Rubl float → display string (`"1 599 ₽"`). Kasr qismi truncate qilinadi
 * (15.99 → "15 ₽"), NaN/Infinity → bo'sh string.
 *
 * Bu Money primitive emas — eski `priceRub` (float) interfeysi bilan
 * ishlaydigan UI joylari uchun (cart item narxlari va h.k.). Yangi kod
 * kopecks-aware `formatMoney(money)` ishlatadi — `lib/format/money.js`.
 *
 * Naming code review: ilgari `formatRubPrice` (`mapProductCard.js`)
 * va `formatRubFloat` (bu fayl) ikkita parallel funksiya edi — turli
 * algoritm (`Math.trunc` vs `Intl.NumberFormat`) va turli NaN-handling.
 * Birlashtirildi shu yerda `formatRubPrice` xulqida (truncate, NaN→"")
 * va `mapProductCard.js` shu import qiladi. Pure — DOMsiz.
 *
 * @param {number} value
 * @returns {string}
 */
export function formatRubFloat(value) {
  const n = Number(value);
  if (!Number.isFinite(n)) return '';
  const rounded = Math.trunc(n);
  const formatted = rounded.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
  return `${formatted} ₽`;
}
