/**
 * Ruscha "товар" so'zining son bilan kelishuvi:
 *   1 товар · 2 товара · 5 товаров
 *
 * `app/checkout/page.jsx` va `app/cart/page.jsx`'da inline takrorlangan edi —
 * audit #1 (god-komponentlar dekompozitsiyasi) doirasida umumiy modulga
 * ko'chirildi. Pure funksiya — oson test qilinadi.
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
