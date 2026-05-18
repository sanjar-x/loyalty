import { describe, it, expect } from 'vitest';

import {
  add,
  compare,
  format,
  formatMoney,
  fromKopecks,
  fromMoneyResponse,
  fromRubFloat,
  isPositive,
  isZero,
  money,
  multiply,
  subtract,
  toRubFloat,
  zeroMoney,
} from '../money';

describe('Money — kopecks-first value type', () => {
  it('zeroMoney/fromKopecks default RUB', () => {
    expect(zeroMoney()).toEqual({ amount: 0, currency: 'RUB' });
    expect(fromKopecks(150000)).toEqual({ amount: 150000, currency: 'RUB' });
  });

  it('non-integer kopecks rejected (preventing float errors)', () => {
    expect(() => fromKopecks(150.5)).toThrow(TypeError);
    expect(() => fromKopecks(NaN)).toThrow(TypeError);
  });

  it('fromMoneyResponse — nullsafe, currency override', () => {
    expect(fromMoneyResponse(null)).toEqual({ amount: 0, currency: 'RUB' });
    expect(fromMoneyResponse(undefined, 'USD')).toEqual({ amount: 0, currency: 'USD' });
    expect(fromMoneyResponse({ amount: 999, currency: 'USD' })).toEqual({
      amount: 999,
      currency: 'USD',
    });
    // If a float arrives, truncate
    expect(fromMoneyResponse({ amount: 100.7, currency: 'RUB' })).toEqual({
      amount: 100,
      currency: 'RUB',
    });
  });

  it('add/subtract — currency mismatch throws', () => {
    const a = fromKopecks(100, 'RUB');
    const b = fromKopecks(50, 'USD');
    expect(() => add(a, b)).toThrow(/currency mismatch/);
    expect(() => subtract(a, b)).toThrow(/currency mismatch/);
  });

  it('add/subtract — basic sum is correct (no float error)', () => {
    // 0.1 + 0.2 RUB = 30 kopecks (would be 0.30000000000000004 in float)
    const a = fromKopecks(10);
    const b = fromKopecks(20);
    expect(add(a, b).amount).toBe(30);
    expect(subtract(b, a).amount).toBe(10);
  });

  it('multiply — multiplied by qty', () => {
    const unit = fromKopecks(150000); // 1500 RUB
    expect(multiply(unit, 3).amount).toBe(450000);
    // If the factor is a float, use Math.round
    expect(multiply(fromKopecks(33), 0.5).amount).toBe(17);
  });

  it('isZero/isPositive/compare', () => {
    expect(isZero(zeroMoney())).toBe(true);
    expect(isPositive(fromKopecks(1))).toBe(true);
    expect(compare(fromKopecks(100), fromKopecks(50))).toBeGreaterThan(0);
    expect(compare(fromKopecks(100), fromKopecks(100))).toBe(0);
  });

  it('format — RUB ru-RU intl', () => {
    const m = fromKopecks(150000);
    const out = format(m);
    expect(out).toMatch(/1.?500/);
    expect(out).toMatch(/₽|RUB/);
  });

  it('toRubFloat/fromRubFloat — migration bridge', () => {
    expect(toRubFloat(fromKopecks(150000))).toBe(1500);
    expect(fromRubFloat(1500).amount).toBe(150000);
    // Float fractions are rounded
    expect(fromRubFloat(0.1).amount).toBe(10);
    expect(fromRubFloat(0.2).amount).toBe(20);
    expect(add(fromRubFloat(0.1), fromRubFloat(0.2)).amount).toBe(30);
  });

  it('immutability — returned object is frozen', () => {
    const m = fromKopecks(100);
    expect(Object.isFrozen(m)).toBe(true);
    expect(() => {
      'use strict';
      m.amount = 0;
    }).toThrow();
  });
});

describe('Money — public aliases (CHK-007)', () => {
  it('money(kopecks) === fromKopecks(kopecks)', () => {
    expect(money(150000)).toEqual(fromKopecks(150000));
    expect(money(0, 'USD')).toEqual(fromKopecks(0, 'USD'));
  });

  it('money — non-integer kopecks rejected (alias preserves contract)', () => {
    expect(() => money(150.5)).toThrow(TypeError);
  });

  it('formatMoney === format (alias parity)', () => {
    const m = fromKopecks(150000);
    expect(formatMoney(m)).toBe(format(m));
  });

  it('formatMoney — fractional kopecks render with 2 decimals when overridden', () => {
    const m = money(15050); // 150.50 RUB
    const out = formatMoney(m, {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });
    expect(out).toMatch(/150[,.]50/);
  });
});
