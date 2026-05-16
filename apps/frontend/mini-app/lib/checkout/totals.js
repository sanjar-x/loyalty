/**
 * Pure totals hisob-kitobi — kopecks integer math.
 *
 * Inputs:
 *  • items[]: { quantity, priceRub, lineTotalRub? }   — legacy rubl float
 *  • quote:  flow.quote — `{ deliveryAmount: kopecks, currency }` yoki null
 *  • promo:  { code, discountRub } yoki null
 *  • points: { applied: number } yoki null  (Loyalty Points moduli yoqilganda)
 *
 * Output (CHK-007): Money primitive maydonlari (`subtotal`, `delivery`,
 * `discount`, `pointsDiscount`, `total`) + BC `*Rub` float getter'lar va
 * `itemCount`, `currency`. Eski UI sinmaydi; yangi UI `formatMoney(total)`
 * orqali render qiladi.
 *
 * Float arifmetika xatolari (`0.1 + 0.2`) bartaraf etiladi — barcha summalar
 * butun kopecks'da.
 */

import { add, multiply, money, subtract, zeroMoney } from '@/lib/format/money';

function kopecksFromRub(rubFloat) {
  const n = Number(rubFloat);
  if (!Number.isFinite(n)) return 0;
  return Math.round(n * 100);
}

function clampToZero(m) {
  if (m.amount >= 0) return m;
  return zeroMoney(m.currency);
}

export function computeCheckoutTotals({
  items = [],
  quote = null,
  promo = null,
  points = null,
} = {}) {
  const currency = quote?.currency || 'RUB';

  let subtotal = zeroMoney(currency);
  let itemCount = 0;
  for (const x of items) {
    const qty = Number(x?.quantity);
    const q = Number.isFinite(qty) && qty > 0 ? Math.floor(qty) : 0;
    itemCount += q;
    if (q === 0) continue;

    // `lineTotalRub` agar mavjud bo'lsa — backend hisoblagan summa (discount/
    // promo line darajasida qo'llanilgan). Aks holda `priceRub * quantity`.
    const line = Number(x?.lineTotalRub);
    if (Number.isFinite(line) && line > 0) {
      subtotal = add(subtotal, money(kopecksFromRub(line), currency));
      continue;
    }
    const price = Number(x?.priceRub);
    if (Number.isFinite(price)) {
      subtotal = add(subtotal, multiply(money(kopecksFromRub(price), currency), q));
    }
  }

  const isEmpty = itemCount === 0;

  // `quote.deliveryAmount` allaqachon kopecks butun son (Spec §8.2).
  const delivery =
    quote && Number.isFinite(quote.deliveryAmount)
      ? money(Math.trunc(Number(quote.deliveryAmount)), currency)
      : null;

  const discount = isEmpty
    ? zeroMoney(currency)
    : Number.isFinite(promo?.discountRub)
      ? clampToZero(money(kopecksFromRub(promo.discountRub), currency))
      : zeroMoney(currency);

  const pointsDiscount = isEmpty
    ? zeroMoney(currency)
    : Number.isFinite(points?.applied)
      ? clampToZero(money(kopecksFromRub(points.applied), currency))
      : zeroMoney(currency);

  let total = subtotal;
  if (delivery) total = add(total, delivery);
  total = subtract(total, discount);
  total = subtract(total, pointsDiscount);
  if (total.amount < 0) total = zeroMoney(currency);

  // BC rubl float getter'lar — eski display joylari bir muddat ushlab turadi.
  // To'liq Money primitive'iga ko'chish alohida ticketda (CHK-007 scope'i —
  // checkout sahifasi). PDP/cart drawer/favorites — keyingi ticketlar.
  return {
    itemCount,
    subtotal,
    delivery,
    discount,
    pointsDiscount,
    total,
    currency,
    get subtotalRub() {
      return this.subtotal.amount / 100;
    },
    get deliveryRub() {
      return this.delivery ? this.delivery.amount / 100 : null;
    },
    get discountRub() {
      return this.discount.amount / 100;
    },
    get pointsRub() {
      return this.pointsDiscount.amount / 100;
    },
    get totalRub() {
      return this.total.amount / 100;
    },
  };
}
