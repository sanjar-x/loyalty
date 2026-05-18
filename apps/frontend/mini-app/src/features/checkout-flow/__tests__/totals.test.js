import { describe, it, expect } from 'vitest';

import { computeCheckoutTotals } from '../lib/totals';

const item = (over = {}) => ({
  quantity: 1,
  priceRub: 1000,
  ...over,
});

describe('computeCheckoutTotals', () => {
  it('returns zeros for empty cart', () => {
    const r = computeCheckoutTotals({ items: [] });
    expect(r).toMatchObject({
      itemCount: 0,
      subtotalRub: 0,
      deliveryRub: null,
      discountRub: 0,
      pointsRub: 0,
      totalRub: 0,
    });
  });

  it('sums lineTotalRub when present, falls back to price * qty', () => {
    const r = computeCheckoutTotals({
      items: [
        item({ quantity: 2, priceRub: 500, lineTotalRub: 950 }), // discount line
        item({ quantity: 3, priceRub: 100 }), // → 300
      ],
    });
    expect(r.itemCount).toBe(5);
    expect(r.subtotalRub).toBe(950 + 300);
  });

  it('adds delivery from quote (kopecks → rub)', () => {
    const r = computeCheckoutTotals({
      items: [item()],
      quote: { deliveryAmount: 19900, currency: 'RUB' }, // 199 ₽
    });
    expect(r.deliveryRub).toBe(199);
    expect(r.totalRub).toBe(1000 + 199);
  });

  it('ignores promo/points when cart is empty', () => {
    const r = computeCheckoutTotals({
      items: [],
      promo: { code: 'X', discountRub: 100 },
      points: { applied: 200 },
    });
    expect(r.discountRub).toBe(0);
    expect(r.pointsRub).toBe(0);
    expect(r.totalRub).toBe(0);
  });

  it('never goes negative', () => {
    const r = computeCheckoutTotals({
      items: [item({ priceRub: 100 })],
      promo: { discountRub: 1000 },
    });
    expect(r.totalRub).toBe(0);
  });

  it('subtracts promo and points from subtotal+delivery', () => {
    const r = computeCheckoutTotals({
      items: [item({ priceRub: 1000 })],
      quote: { deliveryAmount: 19900 },
      promo: { discountRub: 100 },
      points: { applied: 50 },
    });
    expect(r.totalRub).toBe(1000 + 199 - 100 - 50);
  });
});

describe('computeCheckoutTotals — kopecks precision (CHK-007 acceptance)', () => {
  it('3 × 333.33 + delivery 555 → total.amount === 155499', () => {
    const r = computeCheckoutTotals({
      items: [{ quantity: 3, priceRub: 333.33 }],
      quote: { deliveryAmount: 55500, currency: 'RUB' }, // 555 ₽
    });
    expect(r.subtotal.amount).toBe(99999);
    expect(r.delivery.amount).toBe(55500);
    expect(r.total.amount).toBe(155499);
    expect(r.totalRub).toBeCloseTo(1554.99, 5);
  });

  it('10 × 100 - promo 50 → total.amount === 95000', () => {
    const r = computeCheckoutTotals({
      items: [{ quantity: 10, priceRub: 100 }],
      promo: { code: 'X', discountRub: 50 },
    });
    expect(r.subtotal.amount).toBe(100000);
    expect(r.discount.amount).toBe(5000);
    expect(r.total.amount).toBe(95000);
  });

  it('empty cart → total.amount === 0 (no NaN/negative)', () => {
    const r = computeCheckoutTotals({});
    expect(r.subtotal.amount).toBe(0);
    expect(r.total.amount).toBe(0);
    expect(r.delivery).toBeNull();
  });

  it('over-discount → total.amount clamped to 0 (Money primitive)', () => {
    const r = computeCheckoutTotals({
      items: [{ quantity: 1, priceRub: 100 }],
      promo: { discountRub: 1000 },
    });
    expect(r.total.amount).toBe(0);
    expect(r.totalRub).toBe(0);
  });

  it('Money primitive — currency from quote, items inherit', () => {
    const r = computeCheckoutTotals({
      items: [{ quantity: 1, priceRub: 100 }],
      quote: { deliveryAmount: 5000, currency: 'USD' },
    });
    expect(r.subtotal.currency).toBe('USD');
    expect(r.delivery.currency).toBe('USD');
    expect(r.total.currency).toBe('USD');
  });

  it('0.1 + 0.2 RUB lines — no float drift in subtotal', () => {
    const r = computeCheckoutTotals({
      items: [
        { quantity: 1, priceRub: 0.1 },
        { quantity: 1, priceRub: 0.2 },
      ],
    });
    expect(r.subtotal.amount).toBe(30); // 10 + 20 kopecks, no 30.000…04
  });

  it('BC getters mirror Money primitive', () => {
    const r = computeCheckoutTotals({
      items: [{ quantity: 2, priceRub: 100 }],
      quote: { deliveryAmount: 10000 },
      promo: { discountRub: 50 },
    });
    expect(r.subtotalRub).toBe(200);
    expect(r.deliveryRub).toBe(100);
    expect(r.discountRub).toBe(50);
    expect(r.totalRub).toBe(250);
  });
});
