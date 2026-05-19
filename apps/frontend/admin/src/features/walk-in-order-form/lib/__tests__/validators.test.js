import { describe, expect, it } from 'vitest';

import {
  validateDeliveryAmount,
  validateEmail,
  validateInn,
  validateIsoDate,
  validateItemsLength,
  validateNonEmptyString,
  validatePassportNumber,
  validatePassportSerial,
  validatePhone,
  validatePriceOverride,
  validateQuantity,
} from '../validators';

describe('walk-in validators — recipient fields', () => {
  it('accepts E.164-shape phones with optional leading +', () => {
    expect(validatePhone('+79108897762')).toBe(true);
    expect(validatePhone('79108897762')).toBe(true);
    expect(validatePhone('12345678')).toBe(true); // min 8 digits
  });

  it('rejects malformed phones', () => {
    expect(validatePhone('')).toBe(false);
    expect(validatePhone('+7')).toBe(false); // too short
    expect(validatePhone('1234567890123456')).toBe(false); // 16 digits
    expect(validatePhone('+7-910-889-77-62')).toBe(false); // dashes
    expect(validatePhone(null)).toBe(false);
  });

  it('accepts standard emails and rejects garbage', () => {
    expect(validateEmail('ivan@example.com')).toBe(true);
    expect(validateEmail('first.last+tag@sub.domain.co')).toBe(true);
    expect(validateEmail('plainstring')).toBe(false);
    expect(validateEmail('no@dot')).toBe(false);
    expect(validateEmail('')).toBe(false);
  });

  it('enforces passport serial = 4 digits', () => {
    expect(validatePassportSerial('1234')).toBe(true);
    expect(validatePassportSerial('123')).toBe(false);
    expect(validatePassportSerial('12345')).toBe(false);
    expect(validatePassportSerial('12a4')).toBe(false);
  });

  it('enforces passport number = 6 digits', () => {
    expect(validatePassportNumber('567890')).toBe(true);
    expect(validatePassportNumber('56789')).toBe(false);
    expect(validatePassportNumber('5678901')).toBe(false);
  });

  it('enforces INN = 12 digits (no checksum)', () => {
    expect(validateInn('500100732272')).toBe(true);
    expect(validateInn('500100732271')).toBe(true); // bad checksum, still accepted
    expect(validateInn('50010073227')).toBe(false); // 11 digits
    expect(validateInn('5001007322720')).toBe(false); // 13 digits
  });

  it('validates ISO-8601 dates', () => {
    expect(validateIsoDate('2026-05-16')).toBe(true);
    expect(validateIsoDate('1990-01-01')).toBe(true);
    expect(validateIsoDate('2026-13-01')).toBe(false); // invalid month
    expect(validateIsoDate('16-05-2026')).toBe(false);
    expect(validateIsoDate('')).toBe(false);
  });
});

describe('walk-in validators — line items', () => {
  it('quantity must be integer 1..99', () => {
    expect(validateQuantity(1)).toBe(true);
    expect(validateQuantity(99)).toBe(true);
    expect(validateQuantity(0)).toBe(false);
    expect(validateQuantity(100)).toBe(false);
    expect(validateQuantity(1.5)).toBe(false);
  });

  it('items length must be 1..50', () => {
    expect(validateItemsLength([{}])).toBe(true);
    expect(validateItemsLength(new Array(50).fill({}))).toBe(true);
    expect(validateItemsLength([])).toBe(false);
    expect(validateItemsLength(new Array(51).fill({}))).toBe(false);
    expect(validateItemsLength('not-array')).toBe(false);
  });

  it('delivery amount must be non-negative integer', () => {
    expect(validateDeliveryAmount(0)).toBe(true);
    expect(validateDeliveryAmount(1500)).toBe(true);
    expect(validateDeliveryAmount(-1)).toBe(false);
    expect(validateDeliveryAmount(1.5)).toBe(false);
  });
});

describe('walk-in validators — price override', () => {
  it('null override is always ok (no override)', () => {
    expect(validatePriceOverride({ override: null, basePrice: 100 })).toEqual({
      ok: true,
    });
  });

  it('rejects negative or non-integer override', () => {
    expect(
      validatePriceOverride({ override: -1, basePrice: 100 }),
    ).toMatchObject({ ok: false, reason: 'must_be_non_negative_integer' });
    expect(
      validatePriceOverride({ override: 1.5, basePrice: 100 }),
    ).toMatchObject({ ok: false, reason: 'must_be_non_negative_integer' });
  });

  it('rejects overrides above base × MAX_PRICE_OVERRIDE_RATIO (10×)', () => {
    expect(
      validatePriceOverride({ override: 1001, basePrice: 100 }),
    ).toMatchObject({ ok: false, reason: 'above_max_ratio', max: 1000 });
  });

  it('accepts override at and below the ratio boundary', () => {
    expect(validatePriceOverride({ override: 1000, basePrice: 100 })).toEqual({
      ok: true,
    });
    expect(validatePriceOverride({ override: 0, basePrice: 100 })).toEqual({
      ok: true,
    });
  });

  it('rejects when basePrice is missing or invalid', () => {
    expect(
      validatePriceOverride({ override: 100, basePrice: null }),
    ).toMatchObject({ ok: false, reason: 'missing_base_price' });
  });
});

describe('walk-in validators — generic helpers', () => {
  it('non-empty string trims whitespace', () => {
    expect(validateNonEmptyString('  ')).toBe(false);
    expect(validateNonEmptyString('x')).toBe(true);
    expect(validateNonEmptyString('xy', { maxLength: 1 })).toBe(false);
  });
});
