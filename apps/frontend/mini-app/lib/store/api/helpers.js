/**
 * RTK Query — umumiy pure-helper'lar.
 *
 * `lib/store/api/` modullari (endpoint config'lar, instance assembly) shu
 * yerdan transform-yordamchilarini oladi. Audit: frontend-main 2026-05-15
 * — `Audit - Mini App Architecture` P1 #6 (monolit api.js → domen modullari).
 */
import { fromMoneyResponse } from '@/lib/format/money';

/**
 * @deprecated CHK-007. Yangi kod `moneyResponseToMoney(...)` orqali Money
 * primitive oladi (kopecks integer, currency-aware). Bu funksiya legacy
 * `priceRub` (rubl float) interfeysi bilan ishlovchi joylar to'liq Money'ga
 * ko'chguncha saqlanadi.
 */
export function moneyToRub(money) {
  if (money == null) return 0;
  if (typeof money === 'number') return money;
  const amount = Number(money?.amount);
  if (!Number.isFinite(amount)) return 0;
  return amount / 100;
}

/**
 * Backend `MoneyResponse` → frontend Money primitive. Nullsafe.
 * Yangi adapter'lar shu yo'l bilan Money beradi; eski adapter'lar
 * `moneyToRub` bilan rubl float qaytaradi (deprecated, scope tashqari).
 * Hozir bu fayl ichida hech qaerda chaqirilmaydi — call site'lar keyingi
 * ticketda (per-domain) Money'ga ko'chirilganda biriktiriladi.
 */
// Placeholder for upcoming MoneyResponse → Money adapter migration (CHK-007 follow-up).
// Hozircha hech qaerda chaqirilmaydi; ESLint function declaration'larga
// no-unused-vars qoidasini qo'llamaydi, shuning uchun directive shart emas.
export { fromMoneyResponse as moneyResponseToMoney };

export function normalizeCartResponse(raw) {
  if (!raw || typeof raw !== 'object') {
    return {
      id: null,
      status: 'empty',
      total_items: 0,
      total_amount: 0,
      currency: 'RUB',
      items: [],
      groups: [],
    };
  }

  const groups = Array.isArray(raw.groups) ? raw.groups : [];
  const flatItems = [];

  for (const g of groups) {
    const gItems = Array.isArray(g?.items) ? g.items : [];
    for (const it of gItems) {
      if (!it || typeof it !== 'object') continue;
      flatItems.push({
        id: it.id,
        skuId: it.skuId,
        productId: it.productId,
        variantId: it.variantId,
        productName: it.productName ?? '',
        variantLabel: it.variantLabel ?? '',
        imageUrl: it.imageUrl ?? '',
        quantity: Number(it.quantity) || 0,
        priceRub: moneyToRub(it.unitPrice),
        lineTotalRub: moneyToRub(it.lineTotal),
        supplierType: it.supplierType ?? g?.supplierType ?? '',
        addedAt: it.addedAt ?? null,
      });
    }
  }

  return {
    id: raw.id ?? null,
    status: raw.status ?? 'active',
    total_items:
      typeof raw.itemCount === 'number'
        ? raw.itemCount
        : flatItems.reduce((s, x) => s + x.quantity, 0),
    total_amount: moneyToRub(raw.total),
    currency: raw.total?.currency ?? 'RUB',
    items: flatItems,
    groups,
  };
}

export function recalcCartTotals(cart) {
  if (!cart || typeof cart !== 'object') return;
  const items = Array.isArray(cart.items) ? cart.items : [];
  let totalItems = 0;
  let totalAmount = 0;
  for (const it of items) {
    const qty = Number(it?.quantity);
    const q = Number.isFinite(qty) && qty > 0 ? qty : 0;
    totalItems += q;

    const line = Number(it?.lineTotalRub);
    if (Number.isFinite(line) && line > 0) {
      totalAmount += line;
      continue;
    }
    const price = Number(it?.priceRub);
    if (Number.isFinite(price)) totalAmount += price * q;
  }

  cart.total_items = totalItems;
  cart.total_amount = totalAmount;
}
