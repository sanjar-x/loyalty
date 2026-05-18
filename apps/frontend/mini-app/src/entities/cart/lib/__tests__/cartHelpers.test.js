import { describe, it, expect } from 'vitest';

import { moneyToRub, normalizeCartResponse, recalcCartTotals } from '../cartHelpers';

describe('moneyToRub', () => {
  it('возвращает 0 для null/undefined', () => {
    expect(moneyToRub(null)).toBe(0);
    expect(moneyToRub(undefined)).toBe(0);
  });

  it('число — возвращает as-is', () => {
    expect(moneyToRub(150)).toBe(150);
    expect(moneyToRub(0)).toBe(0);
  });

  it('Money объект {amount: kopecks} → рубли (float)', () => {
    expect(moneyToRub({ amount: 15000 })).toBe(150);
    expect(moneyToRub({ amount: 15050 })).toBe(150.5);
  });

  it('Money с amount=NaN/string-not-number → 0', () => {
    expect(moneyToRub({ amount: 'foo' })).toBe(0);
    expect(moneyToRub({ amount: NaN })).toBe(0);
  });
});

describe('normalizeCartResponse', () => {
  it('null/non-object → empty cart shape', () => {
    expect(normalizeCartResponse(null)).toEqual({
      id: null,
      status: 'empty',
      total_items: 0,
      total_amount: 0,
      currency: 'RUB',
      items: [],
      groups: [],
    });
    expect(normalizeCartResponse('foo')).toEqual(
      expect.objectContaining({ id: null, status: 'empty' })
    );
  });

  it('пустой объект → defaults', () => {
    const result = normalizeCartResponse({});
    expect(result.status).toBe('active');
    expect(result.items).toEqual([]);
    expect(result.total_items).toBe(0);
  });

  it('group + items — items flatten в плоский список', () => {
    const raw = {
      id: 'cart-1',
      status: 'active',
      groups: [
        {
          supplierType: 'china',
          items: [
            {
              id: 'item-1',
              skuId: 'sku-1',
              productId: 'p-1',
              variantId: 'v-1',
              productName: 'Sneakers',
              variantLabel: 'White',
              imageUrl: 'http://img/1.jpg',
              quantity: 2,
              unitPrice: { amount: 5000 },
              lineTotal: { amount: 10000 },
            },
          ],
        },
      ],
    };
    const result = normalizeCartResponse(raw);
    expect(result.id).toBe('cart-1');
    expect(result.items).toHaveLength(1);
    expect(result.items[0]).toEqual({
      id: 'item-1',
      skuId: 'sku-1',
      productId: 'p-1',
      variantId: 'v-1',
      productName: 'Sneakers',
      variantLabel: 'White',
      imageUrl: 'http://img/1.jpg',
      quantity: 2,
      priceRub: 50,
      lineTotalRub: 100,
      supplierType: 'china',
      addedAt: null,
    });
    expect(result.total_items).toBe(2);
  });

  it('itemCount предпочтительнее sum', () => {
    const raw = {
      itemCount: 99,
      groups: [{ items: [{ id: 'a', quantity: 1 }] }],
    };
    expect(normalizeCartResponse(raw).total_items).toBe(99);
  });

  it('supplierType из item override-ит group', () => {
    const raw = {
      groups: [
        {
          supplierType: 'china',
          items: [{ id: 'a', quantity: 1, supplierType: 'inStock' }],
        },
      ],
    };
    expect(normalizeCartResponse(raw).items[0].supplierType).toBe('inStock');
  });

  it('items с не-object — пропущены', () => {
    const raw = {
      groups: [{ items: [null, undefined, 'foo', { id: 'a', quantity: 1 }] }],
    };
    expect(normalizeCartResponse(raw).items).toHaveLength(1);
  });
});

describe('recalcCartTotals', () => {
  it('null/non-object — no-op', () => {
    expect(recalcCartTotals(null)).toBeUndefined();
    expect(recalcCartTotals('foo')).toBeUndefined();
  });

  it('пересчитывает total_items + total_amount по lineTotalRub', () => {
    const cart = {
      items: [
        { quantity: 2, lineTotalRub: 100 },
        { quantity: 3, lineTotalRub: 300 },
      ],
    };
    recalcCartTotals(cart);
    expect(cart.total_items).toBe(5);
    expect(cart.total_amount).toBe(400);
  });

  it('fallback на priceRub × quantity если lineTotalRub отсутствует', () => {
    const cart = {
      items: [{ quantity: 4, priceRub: 25 }],
    };
    recalcCartTotals(cart);
    expect(cart.total_items).toBe(4);
    expect(cart.total_amount).toBe(100);
  });

  it('игнорирует невалидные quantity (NaN/<=0)', () => {
    const cart = {
      items: [
        { quantity: 'bad', priceRub: 10 },
        { quantity: -1, priceRub: 10 },
        { quantity: 2, priceRub: 20 },
      ],
    };
    recalcCartTotals(cart);
    expect(cart.total_items).toBe(2);
    expect(cart.total_amount).toBe(40);
  });
});
