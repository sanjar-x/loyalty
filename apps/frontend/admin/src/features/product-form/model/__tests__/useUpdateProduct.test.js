/**
 * Audit 4.1 — `useUpdateProduct.isConcurrencyConflict` recognises
 * the post-Sprint-4 412 OPTIMISTIC_LOCK_FAILED variant alongside the
 * legacy 409. The helper is the only way `useUpdateProduct` decides
 * whether to translate a concurrency failure to the localized
 * "запись изменилась" message — keep the truth-table small and
 * exhaustive so a refactor doesn't silently regress.
 */
import { describe, expect, it } from 'vitest';

import { isConcurrencyConflict } from '../useUpdateProduct';

describe('isConcurrencyConflict', () => {
  it('returns false for null / undefined / non-error inputs', () => {
    expect(isConcurrencyConflict(null)).toBe(false);
    expect(isConcurrencyConflict(undefined)).toBe(false);
    expect(isConcurrencyConflict({})).toBe(false);
  });

  it('matches a vanilla 409 status', () => {
    expect(isConcurrencyConflict({ status: 409 })).toBe(true);
  });

  it('matches a 412 status (post-D0.3 ETag interceptor)', () => {
    expect(isConcurrencyConflict({ status: 412 })).toBe(true);
  });

  it('matches the OPTIMISTIC_LOCK_FAILED ApiError code', () => {
    expect(
      isConcurrencyConflict({ code: 'OPTIMISTIC_LOCK_FAILED', status: 412 }),
    ).toBe(true);
  });

  it('falls back to substring "409" in legacy message-only errors', () => {
    expect(
      isConcurrencyConflict({
        message: 'Request failed with status 409',
      }),
    ).toBe(true);
  });

  it('does not match unrelated 4xx', () => {
    expect(isConcurrencyConflict({ status: 422 })).toBe(false);
    expect(isConcurrencyConflict({ status: 404 })).toBe(false);
    expect(
      isConcurrencyConflict({ message: 'Validation failed', status: 400 }),
    ).toBe(false);
  });
});
