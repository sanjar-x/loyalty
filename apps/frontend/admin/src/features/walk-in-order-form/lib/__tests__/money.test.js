import { describe, expect, it } from 'vitest';

import { formatKopecksForInput, parseRublesToKopecks } from '../money';

describe('parseRublesToKopecks', () => {
  it('parses plain digit string and multiplies by 100', () => {
    expect(parseRublesToKopecks('150')).toBe(15000);
    expect(parseRublesToKopecks('1')).toBe(100);
    expect(parseRublesToKopecks('0')).toBe(0);
  });

  it('treats empty string as 0 (the field was cleared)', () => {
    expect(parseRublesToKopecks('')).toBe(0);
  });

  it('strips non-digit characters', () => {
    expect(parseRublesToKopecks('1 500')).toBe(150000);
    expect(parseRublesToKopecks('1500₽')).toBe(150000);
  });

  it('returns null on non-string input', () => {
    expect(parseRublesToKopecks(undefined)).toBeNull();
    expect(parseRublesToKopecks(null)).toBeNull();
  });

  it('returns null when the kopeck value would overflow safe integers', () => {
    expect(parseRublesToKopecks('100000000000000000')).toBeNull();
  });
});

describe('formatKopecksForInput', () => {
  it('renders rubles as integer string', () => {
    expect(formatKopecksForInput(15000)).toBe('150');
    expect(formatKopecksForInput(100)).toBe('1');
  });

  it('returns empty string for 0 / nullish / negative', () => {
    expect(formatKopecksForInput(0)).toBe('');
    expect(formatKopecksForInput(null)).toBe('');
    expect(formatKopecksForInput(undefined)).toBe('');
    expect(formatKopecksForInput(-100)).toBe('');
  });

  it('floors fractional kopecks (state should never hold them, but be defensive)', () => {
    expect(formatKopecksForInput(15050)).toBe('150');
  });
});
