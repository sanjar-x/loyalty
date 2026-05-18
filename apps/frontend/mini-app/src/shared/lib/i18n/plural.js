/**
 * Russian plural agreement for the word "товар":
 *   1 → "товар" · 2 → "товара" · 5 → "товаров"
 *
 * Previously duplicated inline in `app/checkout/page.jsx` and
 * `app/cart/page.jsx` — moved to a shared module as part of audit #1
 * (god-component decomposition). Pure function — easy to test.
 *
 * @param {number} count
 * @returns {'товар' | 'товара' | 'товаров'}
 */
export function pluralizeItemsRu(count) {
  const n = Math.abs(count);
  const mod10 = n % 10;
  const mod100 = n % 100;
  if (mod10 === 1 && mod100 !== 11) return 'товар';
  if (mod10 >= 2 && mod10 <= 4 && !(mod100 >= 12 && mod100 <= 14)) return 'товара';
  return 'товаров';
}
