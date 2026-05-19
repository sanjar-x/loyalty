import { describe, expect, it } from 'vitest';

import { maskPassportNumber } from '../lib/maskPassportNumber';

describe('maskPassportNumber', () => {
  it('masks the middle 4 digits of a 6-digit number, keeping first and last', () => {
    expect(maskPassportNumber('1234', '567890')).toBe('1234 5****0');
    expect(maskPassportNumber('1234567890')).toBe('1234 5****0');
  });

  it('strips formatting characters before masking', () => {
    expect(maskPassportNumber('12 34', '56 78 90')).toBe('1234 5****0');
    expect(maskPassportNumber('1234-567890')).toBe('1234 5****0');
  });

  it('returns the original input when the lengths do not match', () => {
    expect(maskPassportNumber('123', '4')).toBe('1234'); // collapsed digits
    expect(maskPassportNumber('')).toBe('');
    expect(maskPassportNumber(null)).toBe('');
    expect(maskPassportNumber(undefined, undefined)).toBe('');
  });

  it('handles non-string inputs defensively', () => {
    expect(maskPassportNumber(1234567890)).toBe('');
  });
});
