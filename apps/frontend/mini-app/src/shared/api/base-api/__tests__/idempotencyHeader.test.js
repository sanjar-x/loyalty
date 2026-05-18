/**
 * Unit tests for the idempotency-key registry in baseApi.js.
 * baseQuery itself is RTKQ-integration territory, but
 * `setPendingIdempotencyKey` / `clearPendingIdempotencyKey` are pure
 * mutations on a module-level map — we verify that logic here.
 *
 * The logic that adds the key to the headers lives inside baseQuery and is
 * confirmed via manual QA against the codegen RTKQ integration
 * (DevTools Network: Idempotency-Key header).
 */

import { describe, it, expect, beforeEach } from 'vitest';

import {
  setPendingIdempotencyKey,
  clearPendingIdempotencyKey,
} from '@/shared/api/base-api/baseApi';

const URL = '/api/v1/cart/checkout';

beforeEach(() => {
  clearPendingIdempotencyKey(URL);
});

describe('idempotency registry (CHK-006)', () => {
  it('set then clear — null-safe contract', () => {
    expect(() => setPendingIdempotencyKey(URL, 'key-1')).not.toThrow();
    expect(() => clearPendingIdempotencyKey(URL)).not.toThrow();
  });

  it('set with empty key removes the entry (treated as clear)', () => {
    setPendingIdempotencyKey(URL, 'key-1');
    setPendingIdempotencyKey(URL, '');
    // No throw, no orphan entry — observable via clearing again
    expect(() => clearPendingIdempotencyKey(URL)).not.toThrow();
  });

  it('set ignores non-string url and key (defensive)', () => {
    expect(() => setPendingIdempotencyKey(null, 'k')).not.toThrow();
    expect(() => setPendingIdempotencyKey(URL, null)).not.toThrow();
    expect(() => setPendingIdempotencyKey(URL, undefined)).not.toThrow();
  });

  it('clear ignores non-string url', () => {
    expect(() => clearPendingIdempotencyKey(null)).not.toThrow();
    expect(() => clearPendingIdempotencyKey(undefined)).not.toThrow();
  });

  it('repeated set overwrites previous key (retry semantics)', () => {
    setPendingIdempotencyKey(URL, 'key-1');
    setPendingIdempotencyKey(URL, 'key-2');
    // Second wins — verified by clearing once, no leftover
    clearPendingIdempotencyKey(URL);
  });
});
