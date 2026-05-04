import { describe, it, expect } from "vitest";

import { computeCheckoutTotals } from "../totals";

const item = (over = {}) => ({
  quantity: 1,
  priceRub: 1000,
  ...over,
});

describe("computeCheckoutTotals", () => {
  it("returns zeros for empty cart", () => {
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

  it("sums lineTotalRub when present, falls back to price * qty", () => {
    const r = computeCheckoutTotals({
      items: [
        item({ quantity: 2, priceRub: 500, lineTotalRub: 950 }), // discount line
        item({ quantity: 3, priceRub: 100 }), // → 300
      ],
    });
    expect(r.itemCount).toBe(5);
    expect(r.subtotalRub).toBe(950 + 300);
  });

  it("adds delivery from quote (kopecks → rub)", () => {
    const r = computeCheckoutTotals({
      items: [item()],
      quote: { deliveryAmount: 19900, currency: "RUB" }, // 199 ₽
    });
    expect(r.deliveryRub).toBe(199);
    expect(r.totalRub).toBe(1000 + 199);
  });

  it("ignores promo/points when cart is empty", () => {
    const r = computeCheckoutTotals({
      items: [],
      promo: { code: "X", discountRub: 100 },
      points: { applied: 200 },
    });
    expect(r.discountRub).toBe(0);
    expect(r.pointsRub).toBe(0);
    expect(r.totalRub).toBe(0);
  });

  it("never goes negative", () => {
    const r = computeCheckoutTotals({
      items: [item({ priceRub: 100 })],
      promo: { discountRub: 1000 },
    });
    expect(r.totalRub).toBe(0);
  });

  it("subtracts promo and points from subtotal+delivery", () => {
    const r = computeCheckoutTotals({
      items: [item({ priceRub: 1000 })],
      quote: { deliveryAmount: 19900 },
      promo: { discountRub: 100 },
      points: { applied: 50 },
    });
    expect(r.totalRub).toBe(1000 + 199 - 100 - 50);
  });
});
