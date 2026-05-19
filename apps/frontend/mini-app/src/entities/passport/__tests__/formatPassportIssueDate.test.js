import { describe, expect, it } from 'vitest';

import { formatPassportIssueDate } from '../lib/formatPassportIssueDate';

describe('formatPassportIssueDate', () => {
  it('reformats ISO date to RU DD.MM.YYYY', () => {
    expect(formatPassportIssueDate('1995-06-12')).toBe('12.06.1995');
    expect(formatPassportIssueDate('2024-01-01')).toBe('01.01.2024');
  });

  it('trims surrounding whitespace before parsing', () => {
    expect(formatPassportIssueDate('  2020-02-29  ')).toBe('29.02.2020');
  });

  it('returns empty string on null, undefined, non-string, or wrong format', () => {
    expect(formatPassportIssueDate('')).toBe('');
    expect(formatPassportIssueDate(null)).toBe('');
    expect(formatPassportIssueDate(undefined)).toBe('');
    expect(formatPassportIssueDate(20200229)).toBe('');
    expect(formatPassportIssueDate('29.02.2020')).toBe('');
    expect(formatPassportIssueDate('1995-6-12')).toBe(''); // missing zero pad
  });
});
