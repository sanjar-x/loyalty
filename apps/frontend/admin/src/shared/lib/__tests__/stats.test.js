/**
 * Regression tests for shared/lib/stats — period statistics + range
 * inclusion (FA-403c). Three pure functions, zero tests today, used by
 * <TopMetrics> on the admin /orders page (and likely by any future
 * dashboard surface). This file locks the contract.
 *
 * Time strategy:
 *   vi.setSystemTime(new Date('2026-05-15T12:00:00Z')) — UTC noon, far
 *   from day-boundary in any timezone, so fixtures stay deterministic
 *   across CI/local TZ. Real dayjs respects the frozen clock.
 *
 * Locale note:
 *   The shared dayjs is configured with the ru locale (week starts on
 *   Monday). For the fixed clock 2026-05-15 (Friday):
 *     - day:   2026-05-15 ; previous = 2026-05-14
 *     - week:  Mon 2026-05-11 → Sun 2026-05-17 ; previous = May 4 → May 10
 *     - month: 2026-05-01 → 2026-05-31 ; previous = April 1 → April 30
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import dayjs from '@/shared/lib/dayjs';

import {
  calculatePeriodStats,
  calculatePeriodSum,
  isWithinRange,
} from '../stats';

const FIXED_NOW = new Date('2026-05-15T12:00:00Z');

beforeEach(() => {
  vi.useFakeTimers();
  vi.setSystemTime(FIXED_NOW);
});

afterEach(() => {
  vi.useRealTimers();
});

describe('calculatePeriodStats', () => {
  it('counts items in current scope vs previous scope and returns percent change', () => {
    const items = [
      { createdAt: '2026-05-15T08:00:00Z' }, // current day
      { createdAt: '2026-05-15T15:00:00Z' }, // current day
      { createdAt: '2026-05-14T08:00:00Z' }, // previous day
    ];
    const result = calculatePeriodStats(items, 'createdAt', 'day');
    expect(result.value).toBe(2);
    expect(result.change).toBe(100); // (2-1)/1 * 100
  });

  it('returns 100% change when previous count is zero and current is positive', () => {
    const items = [{ createdAt: '2026-05-15T10:00:00Z' }];
    const result = calculatePeriodStats(items, 'createdAt', 'day');
    expect(result.value).toBe(1);
    expect(result.change).toBe(100);
  });

  it('returns 0% change when both current and previous are zero', () => {
    const result = calculatePeriodStats([], 'createdAt', 'day');
    expect(result.value).toBe(0);
    expect(result.change).toBe(0);
  });

  it('returns a negative change when current is less than previous', () => {
    const items = [
      { createdAt: '2026-05-15T10:00:00Z' }, // current = 1
      { createdAt: '2026-05-14T08:00:00Z' }, // previous = 2
      { createdAt: '2026-05-14T15:00:00Z' },
    ];
    const result = calculatePeriodStats(items, 'createdAt', 'day');
    expect(result.value).toBe(1);
    expect(result.change).toBe(-50); // (1-2)/2 * 100
  });

  it('rounds the change to the nearest integer', () => {
    const items = [
      { createdAt: '2026-05-15T10:00:00Z' }, // current = 1
      { createdAt: '2026-05-14T08:00:00Z' }, // previous = 3
      { createdAt: '2026-05-14T10:00:00Z' },
      { createdAt: '2026-05-14T12:00:00Z' },
    ];
    const result = calculatePeriodStats(items, 'createdAt', 'day');
    // (1-3)/3 * 100 = -66.666... → Math.round → -67
    expect(result.change).toBe(-67);
  });

  it('respects the scope argument ("week" / "month")', () => {
    const items = [
      // Current week (Mon May 11 – Sun May 17)
      { createdAt: '2026-05-12T10:00:00Z' }, // Tue
      { createdAt: '2026-05-15T10:00:00Z' }, // Fri (today)
      // Previous week (May 4 – May 10)
      { createdAt: '2026-05-08T10:00:00Z' }, // Fri
    ];
    expect(calculatePeriodStats(items, 'createdAt', 'week').value).toBe(2);
    expect(calculatePeriodStats(items, 'createdAt', 'week').change).toBe(100);

    // All three live in May → current month = 3; previous (April) = 0 → 100
    expect(calculatePeriodStats(items, 'createdAt', 'month').value).toBe(3);
    expect(calculatePeriodStats(items, 'createdAt', 'month').change).toBe(100);
  });
});

describe('calculatePeriodSum', () => {
  it('sums the value field for items in current scope and computes change', () => {
    const items = [
      { createdAt: '2026-05-15T08:00:00Z', total: 100 }, // current
      { createdAt: '2026-05-15T15:00:00Z', total: 200 }, // current
      { createdAt: '2026-05-14T10:00:00Z', total: 50 }, // previous
    ];
    const result = calculatePeriodSum(items, 'createdAt', 'total', 'day');
    expect(result.value).toBe(300);
    expect(result.change).toBe(500); // (300-50)/50 * 100
  });

  it('returns 100% change when previous sum is zero and current is positive', () => {
    const items = [{ createdAt: '2026-05-15T10:00:00Z', total: 250 }];
    const result = calculatePeriodSum(items, 'createdAt', 'total', 'day');
    expect(result.value).toBe(250);
    expect(result.change).toBe(100);
  });

  it('returns 0% change when both sums are zero', () => {
    const result = calculatePeriodSum([], 'createdAt', 'total', 'day');
    expect(result.value).toBe(0);
    expect(result.change).toBe(0);
  });
});

describe('isWithinRange', () => {
  it('returns false when range.from is missing', () => {
    expect(
      isWithinRange('2026-05-15T10:00:00Z', {
        from: null,
        to: dayjs('2026-05-16'),
      }),
    ).toBe(false);
  });

  it('returns false when range.to is missing', () => {
    expect(
      isWithinRange('2026-05-15T10:00:00Z', {
        from: dayjs('2026-05-14'),
        to: null,
      }),
    ).toBe(false);
  });

  it('returns false when both bounds are null', () => {
    expect(
      isWithinRange('2026-05-15T10:00:00Z', { from: null, to: null }),
    ).toBe(false);
  });

  it('returns true for a date strictly inside [from.startOf(day), to.endOf(day)]', () => {
    const range = { from: dayjs('2026-05-14'), to: dayjs('2026-05-16') };
    expect(isWithinRange('2026-05-15T10:00:00Z', range)).toBe(true);
  });

  it('treats `from` as start-of-day and `to` as end-of-day (boundary inclusive)', () => {
    const range = { from: dayjs('2026-05-14'), to: dayjs('2026-05-16') };
    // Local-day boundaries — 00:00:00 of from-day and 23:59:59 of to-day
    // both fall inside the inclusive range.
    expect(isWithinRange('2026-05-14T00:00:00', range)).toBe(true);
    expect(isWithinRange('2026-05-16T23:59:59', range)).toBe(true);
  });

  it('returns false for dates strictly outside the inclusive range', () => {
    const range = { from: dayjs('2026-05-14'), to: dayjs('2026-05-16') };
    // Local-time strings (no Z) keep the boundary semantics unambiguous
    // across CI/local TZ. May 13 mid-day is fully before the range; May 17
    // mid-day is fully after.
    expect(isWithinRange('2026-05-13T12:00:00', range)).toBe(false);
    expect(isWithinRange('2026-05-17T12:00:00', range)).toBe(false);
  });
});
