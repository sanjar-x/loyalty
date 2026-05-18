/**
 * Checkout-specific error predicates. Sprint 2.2: extracted from
 * shared/api/errors (which used to hold business-domain codes for delivery
 * quote / provider retry / currency mismatch — not "transport plumbing").
 *
 * The base `normalizeApiError`, `isTokenExpiredError`, `humanizeApiError`
 * remain in shared/api/errors — those are transport-level.
 */

import { normalizeApiError } from '@/shared/api/errors';

// CHK-024: `ORDER_DELIVERY_QUOTE_EXPIRED` — the backend returns this on /orders
// when the quote has passed its TTL (30 min). placeOrder performs one auto-refresh + retry.
const QUOTE_EXPIRY_CODES = new Set([
  'QUOTE_EXPIRED',
  'QUOTE_NOT_FOUND',
  'ORDER_DELIVERY_QUOTE_EXPIRED',
]);

// CHK-024: provider list empty (cache miss / disabled) or provider API
// HTTP/timeout error — both are retryable.
const PROVIDER_RETRY_CODES = new Set([
  'RATE_CALCULATION_ERROR',
  'RATE_CALCULATION_FAILED',
  'NO_ELIGIBLE_PROVIDERS',
  'BOOKING_ERROR',
  'PROVIDER_UNAVAILABLE',
  'BOOKING_PENDING',
]);

// CHK-024: backend currency mismatch (cart vs quote) — should not happen
// for the same provider; backend bug → Sentry log + simple toast to the user.
const CURRENCY_MISMATCH_CODES = new Set(['ORDER_DELIVERY_QUOTE_CURRENCY_MISMATCH']);

export function isQuoteExpiredError(rtkError) {
  const e = normalizeApiError(rtkError);
  return QUOTE_EXPIRY_CODES.has(e.code);
}

export function isProviderRetryableError(rtkError) {
  const e = normalizeApiError(rtkError);
  if (PROVIDER_RETRY_CODES.has(e.code)) return true;
  return e.status === 502 || e.status === 503;
}

export function isCurrencyMismatchError(rtkError) {
  const e = normalizeApiError(rtkError);
  return CURRENCY_MISMATCH_CODES.has(e.code);
}
