/**
 * RTK Query — shared pure helpers.
 *
 * `lib/store/api/` modules (endpoint configs, instance assembly) pull
 * their transform helpers from here. Audit: frontend-main 2026-05-15
 * — `Audit - Mini App Architecture` P1 #6 (monolithic api.js → domain modules).
 */
/**
 * @deprecated CHK-007. New code uses the Money primitive (integer kopecks).
 * This function is kept until call sites that work with the legacy
 * `priceRub` (ruble float) interface are fully migrated to Money.
 */
export function moneyToRub(money) {
  if (money == null) return 0;
  if (typeof money === 'number') return money;
  const amount = Number(money?.amount);
  if (!Number.isFinite(amount)) return 0;
  return amount / 100;
}

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
