import { describe, it, expect, vi, afterEach } from 'vitest';

import { parseRuDate, toRuDate, formatRuDateMask } from '../dateFormat';

describe('parseRuDate', () => {
  it('converts valid DD.MM.YYYY → YYYY-MM-DD', () => {
    expect(parseRuDate('15.03.1990')).toBe('1990-03-15');
  });

  it('supports leap year (29.02.2024 valid)', () => {
    expect(parseRuDate('29.02.2024')).toBe('2024-02-29');
  });

  it('rejects non-leap Feb 29 (29.02.2023)', () => {
    expect(parseRuDate('29.02.2023')).toBeNull();
  });

  it('rejects 31.02 (Date constructor normalizes — caught by component check)', () => {
    expect(parseRuDate('31.02.1990')).toBeNull();
  });

  it('rejects 30.02 for any year', () => {
    expect(parseRuDate('30.02.2000')).toBeNull();
  });

  it('rejects 31.04 (April has 30 days)', () => {
    expect(parseRuDate('31.04.2020')).toBeNull();
  });

  it('rejects year < 1900', () => {
    expect(parseRuDate('01.01.1850')).toBeNull();
  });

  it('rejects year > currentYear + 1', () => {
    const tooFar = new Date().getFullYear() + 5;
    expect(parseRuDate(`01.01.${tooFar}`)).toBeNull();
  });

  it('accepts currentYear + 1 (issueDate near-future tolerance)', () => {
    const nextYear = new Date().getFullYear() + 1;
    expect(parseRuDate(`01.01.${nextYear}`)).toBe(`${nextYear}-01-01`);
  });

  it('rejects month 13', () => {
    expect(parseRuDate('15.13.2000')).toBeNull();
  });

  it('rejects month 00', () => {
    expect(parseRuDate('15.00.2000')).toBeNull();
  });

  it('rejects day 00', () => {
    expect(parseRuDate('00.01.2000')).toBeNull();
  });

  it('rejects empty string', () => {
    expect(parseRuDate('')).toBeNull();
  });

  it('rejects null/undefined', () => {
    expect(parseRuDate(null)).toBeNull();
    expect(parseRuDate(undefined)).toBeNull();
  });

  it('rejects malformed string (no dots)', () => {
    expect(parseRuDate('15031990')).toBeNull();
  });

  it('rejects ISO format input (already YYYY-MM-DD)', () => {
    expect(parseRuDate('1990-03-15')).toBeNull();
  });

  it('rejects single-digit day/month', () => {
    expect(parseRuDate('1.3.1990')).toBeNull();
  });

  it('trims surrounding whitespace', () => {
    expect(parseRuDate('  15.03.1990  ')).toBe('1990-03-15');
  });
});

describe('toRuDate', () => {
  it('converts ISO → DD.MM.YYYY', () => {
    expect(toRuDate('1990-03-15')).toBe('15.03.1990');
  });

  it('preserves zero-padding', () => {
    expect(toRuDate('2000-01-05')).toBe('05.01.2000');
  });

  it('returns empty string for malformed input', () => {
    expect(toRuDate('not-a-date')).toBe('');
    expect(toRuDate('15.03.1990')).toBe('');
    expect(toRuDate('')).toBe('');
    expect(toRuDate(null)).toBe('');
  });
});

describe('formatRuDateMask', () => {
  it('inserts dots progressively', () => {
    expect(formatRuDateMask('1')).toBe('1');
    expect(formatRuDateMask('15')).toBe('15');
    expect(formatRuDateMask('150')).toBe('15.0');
    expect(formatRuDateMask('1503')).toBe('15.03');
    expect(formatRuDateMask('15031')).toBe('15.03.1');
    expect(formatRuDateMask('15031990')).toBe('15.03.1990');
  });

  it('truncates to 8 digits', () => {
    expect(formatRuDateMask('150319901234')).toBe('15.03.1990');
  });

  it('strips non-digits before formatting', () => {
    expect(formatRuDateMask('15a03b1990')).toBe('15.03.1990');
    expect(formatRuDateMask('15.03.1990')).toBe('15.03.1990');
  });

  it('handles empty/invalid input', () => {
    expect(formatRuDateMask('')).toBe('');
    expect(formatRuDateMask(null)).toBe('');
    expect(formatRuDateMask(undefined)).toBe('');
  });
});

describe('parseRuDate boundary — year cap is dynamic', () => {
  const RealDate = Date;
  afterEach(() => {
    vi.useRealTimers();
    globalThis.Date = RealDate;
  });

  it('uses real current year for upper bound', () => {
    vi.setSystemTime(new Date(2030, 5, 15));
    expect(parseRuDate('01.01.2031')).toBe('2031-01-01');
    expect(parseRuDate('01.01.2032')).toBeNull();
  });
});
