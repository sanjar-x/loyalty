/**
 * Sprint 2.2: checkout-specific error predicate tests — moved from
 * shared/api/__tests__/errors.test.js (they were checking the business
 * domain of delivery quote / provider retry / currency mismatch).
 */
import { describe, it, expect } from 'vitest';

import {
  isQuoteExpiredError,
  isProviderRetryableError,
  isCurrencyMismatchError,
} from '../lib/errors';

function envelope(code, message = '', status = 422) {
  return {
    status,
    data: { error: { code, message, details: null, request_id: 'req-1' } },
  };
}

describe('isQuoteExpiredError (CHK-024: new code ORDER_DELIVERY_QUOTE_EXPIRED)', () => {
  it('classic QUOTE_EXPIRED', () => {
    expect(isQuoteExpiredError(envelope('QUOTE_EXPIRED'))).toBe(true);
  });

  it('QUOTE_NOT_FOUND', () => {
    expect(isQuoteExpiredError(envelope('QUOTE_NOT_FOUND'))).toBe(true);
  });

  it('ORDER_DELIVERY_QUOTE_EXPIRED (new, CHK-024)', () => {
    expect(isQuoteExpiredError(envelope('ORDER_DELIVERY_QUOTE_EXPIRED'))).toBe(true);
  });

  it('unrelated code — false', () => {
    expect(isQuoteExpiredError(envelope('SOMETHING_ELSE'))).toBe(false);
  });
});

describe('isProviderRetryableError (CHK-024: NO_ELIGIBLE_PROVIDERS, RATE_CALCULATION_FAILED)', () => {
  it('NO_ELIGIBLE_PROVIDERS (new)', () => {
    expect(isProviderRetryableError(envelope('NO_ELIGIBLE_PROVIDERS'))).toBe(true);
  });

  it('RATE_CALCULATION_FAILED (new)', () => {
    expect(isProviderRetryableError(envelope('RATE_CALCULATION_FAILED'))).toBe(true);
  });

  it('classic provider codes', () => {
    expect(isProviderRetryableError(envelope('RATE_CALCULATION_ERROR'))).toBe(true);
    expect(isProviderRetryableError(envelope('PROVIDER_UNAVAILABLE'))).toBe(true);
    expect(isProviderRetryableError(envelope('BOOKING_PENDING'))).toBe(true);
  });

  it('HTTP 502/503 — retryable regardless of code', () => {
    expect(isProviderRetryableError(envelope('', '', 502))).toBe(true);
    expect(isProviderRetryableError(envelope('', '', 503))).toBe(true);
  });

  it('500 — NOT retryable (different category)', () => {
    expect(isProviderRetryableError(envelope('', '', 500))).toBe(false);
  });
});

describe('isCurrencyMismatchError (CHK-024)', () => {
  it('ORDER_DELIVERY_QUOTE_CURRENCY_MISMATCH', () => {
    expect(isCurrencyMismatchError(envelope('ORDER_DELIVERY_QUOTE_CURRENCY_MISMATCH'))).toBe(true);
  });

  it('other code — false', () => {
    expect(isCurrencyMismatchError(envelope('SOMETHING'))).toBe(false);
  });
});
