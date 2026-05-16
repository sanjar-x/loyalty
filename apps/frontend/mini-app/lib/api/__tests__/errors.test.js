import { describe, it, expect } from 'vitest';

import {
  normalizeApiError,
  isTokenExpiredError,
  isQuoteExpiredError,
  isProviderRetryableError,
  isCurrencyMismatchError,
} from '../errors';

function envelope(code, message = '', status = 422) {
  return {
    status,
    data: { error: { code, message, details: null, request_id: 'req-1' } },
  };
}

describe('normalizeApiError', () => {
  it('возвращает каноническую форму для backend envelope', () => {
    const n = normalizeApiError(envelope('SOMETHING', 'msg'));
    expect(n).toEqual({
      status: 422,
      code: 'SOMETHING',
      message: 'msg',
      details: null,
      requestId: 'req-1',
    });
  });

  it('FETCH_ERROR (string status) — code сохраняется', () => {
    const n = normalizeApiError({ status: 'FETCH_ERROR', error: 'Failed' });
    expect(n.code).toBe('FETCH_ERROR');
    expect(n.message).toBe('Failed');
  });
});

describe('isQuoteExpiredError (CHK-024: новый код ORDER_DELIVERY_QUOTE_EXPIRED)', () => {
  it('классический QUOTE_EXPIRED', () => {
    expect(isQuoteExpiredError(envelope('QUOTE_EXPIRED'))).toBe(true);
  });

  it('QUOTE_NOT_FOUND', () => {
    expect(isQuoteExpiredError(envelope('QUOTE_NOT_FOUND'))).toBe(true);
  });

  it('ORDER_DELIVERY_QUOTE_EXPIRED (новый, CHK-024)', () => {
    expect(isQuoteExpiredError(envelope('ORDER_DELIVERY_QUOTE_EXPIRED'))).toBe(true);
  });

  it('посторонний код — false', () => {
    expect(isQuoteExpiredError(envelope('SOMETHING_ELSE'))).toBe(false);
  });
});

describe('isProviderRetryableError (CHK-024: NO_ELIGIBLE_PROVIDERS, RATE_CALCULATION_FAILED)', () => {
  it('NO_ELIGIBLE_PROVIDERS (новый)', () => {
    expect(isProviderRetryableError(envelope('NO_ELIGIBLE_PROVIDERS'))).toBe(true);
  });

  it('RATE_CALCULATION_FAILED (новый)', () => {
    expect(isProviderRetryableError(envelope('RATE_CALCULATION_FAILED'))).toBe(true);
  });

  it('классические провайдер-коды', () => {
    expect(isProviderRetryableError(envelope('RATE_CALCULATION_ERROR'))).toBe(true);
    expect(isProviderRetryableError(envelope('PROVIDER_UNAVAILABLE'))).toBe(true);
    expect(isProviderRetryableError(envelope('BOOKING_PENDING'))).toBe(true);
  });

  it('HTTP 502/503 — retryable вне зависимости от code', () => {
    expect(isProviderRetryableError(envelope('', '', 502))).toBe(true);
    expect(isProviderRetryableError(envelope('', '', 503))).toBe(true);
  });

  it('500 — НЕ retryable (другая категория)', () => {
    expect(isProviderRetryableError(envelope('', '', 500))).toBe(false);
  });
});

describe('isCurrencyMismatchError (CHK-024)', () => {
  it('ORDER_DELIVERY_QUOTE_CURRENCY_MISMATCH', () => {
    expect(isCurrencyMismatchError(envelope('ORDER_DELIVERY_QUOTE_CURRENCY_MISMATCH'))).toBe(true);
  });

  it('другой код — false', () => {
    expect(isCurrencyMismatchError(envelope('SOMETHING'))).toBe(false);
  });
});

describe('isTokenExpiredError (sanity)', () => {
  it('401 без кода — true', () => {
    expect(isTokenExpiredError(envelope('', '', 401))).toBe(true);
  });

  it('TOKEN_EXPIRED код', () => {
    expect(isTokenExpiredError(envelope('TOKEN_EXPIRED'))).toBe(true);
  });
});
