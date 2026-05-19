import { describe, expect, it } from 'vitest';

import { isValidInn } from '../index';

/**
 * Reference vectors:
 *  • 500100732259 — valid (Минфин wiki example)
 *  • 526317984689 — valid (generated locally with the same algorithm)
 *  • 500100732250 — flipped last digit, must fail
 *  • 500100732159 — flipped 11th digit, must fail
 */
describe('isValidInn', () => {
  it('accepts a 12-digit ИНН with valid mod-11-twice checksums', () => {
    expect(isValidInn('500100732259')).toBe(true);
    expect(isValidInn('526317984689')).toBe(true);
  });

  it('rejects last-digit mismatch', () => {
    expect(isValidInn('500100732250')).toBe(false);
  });

  it('rejects 11th-digit mismatch', () => {
    expect(isValidInn('500100732159')).toBe(false);
  });

  it('rejects empty / non-string / wrong-length input', () => {
    expect(isValidInn('')).toBe(false);
    expect(isValidInn(null)).toBe(false);
    expect(isValidInn(undefined)).toBe(false);
    expect(isValidInn(500100732259)).toBe(false);
    expect(isValidInn('1234567890')).toBe(false); // 10-digit юрлицо form
    expect(isValidInn('1234567890123')).toBe(false); // 13-digit
  });

  it('strips formatting characters before validating', () => {
    expect(isValidInn('5001 0073 2259')).toBe(true);
    expect(isValidInn('5001-0073-2259')).toBe(true);
  });
});
