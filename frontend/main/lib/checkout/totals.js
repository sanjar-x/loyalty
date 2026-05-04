/**
 * Pure totals hisob-kitobi — testable, server-trusted.
 *
 * Inputs:
 *  • items[]: { quantity, priceRub, lineTotalRub? }
 *  • quote:  flow.quote — `{ deliveryAmount: kopecks, currency }` yoki null
 *  • promo:  { code, discountRub } yoki null
 *  • points: { applied: number } yoki null  (Loyalty Points moduli yoqilganda)
 *
 * Output: { subtotalRub, deliveryRub, discountRub, pointsRub, totalRub, currency }
 *
 * Eslatma:
 *  - `quote.deliveryAmount` backend kopecks'da, ruble'ga o'tkaziladi.
 *  - quote yo'q bo'lsa `deliveryRub = null` — UI "Рассчитывается..." ko'rsatadi.
 *  - itemCount=0 bo'lsa hech qanday discount/points qo'llanilmaydi.
 */

export function computeCheckoutTotals({
  items = [],
  quote = null,
  promo = null,
  points = null,
} = {}) {
  let subtotalRub = 0;
  let itemCount = 0;
  for (const x of items) {
    const qty = Number(x?.quantity);
    const q = Number.isFinite(qty) && qty > 0 ? qty : 0;
    itemCount += q;

    const line = Number(x?.lineTotalRub);
    if (Number.isFinite(line) && line > 0) {
      subtotalRub += line;
      continue;
    }
    const price = Number(x?.priceRub);
    if (Number.isFinite(price)) subtotalRub += price * q;
  }

  const isEmpty = itemCount === 0;

  const deliveryRub =
    quote && Number.isFinite(quote.deliveryAmount)
      ? quote.deliveryAmount / 100
      : null;

  const discountRub = isEmpty
    ? 0
    : Number.isFinite(promo?.discountRub)
      ? Math.max(0, promo.discountRub)
      : 0;

  const pointsRub = isEmpty
    ? 0
    : Number.isFinite(points?.applied)
      ? Math.max(0, points.applied)
      : 0;

  const totalRub = Math.max(
    0,
    subtotalRub + (deliveryRub ?? 0) - discountRub - pointsRub,
  );

  return {
    itemCount,
    subtotalRub,
    deliveryRub,
    discountRub,
    pointsRub,
    totalRub,
    currency: quote?.currency || "RUB",
  };
}
