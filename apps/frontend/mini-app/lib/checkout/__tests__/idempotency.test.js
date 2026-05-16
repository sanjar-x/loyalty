import { describe, it, expect, vi } from 'vitest';

import { acquireInflight, releaseInflight, ensureKey, resetKey, safeUUID } from '../idempotency';

describe('idempotency primitives (CHK-006)', () => {
  it('acquireInflight — first acquire succeeds, second blocked', () => {
    const ref = { current: false };
    expect(acquireInflight(ref)).toBe(true);
    expect(ref.current).toBe(true);
    expect(acquireInflight(ref)).toBe(false);
  });

  it('releaseInflight — flips back to false', () => {
    const ref = { current: true };
    releaseInflight(ref);
    expect(ref.current).toBe(false);
    // re-acquire after release
    expect(acquireInflight(ref)).toBe(true);
  });

  it('acquireInflight/releaseInflight — null-safe', () => {
    expect(acquireInflight(null)).toBe(false);
    expect(acquireInflight(undefined)).toBe(false);
    expect(() => releaseInflight(null)).not.toThrow();
  });

  it('ensureKey — generates once, reuses on subsequent calls (retry semantics)', () => {
    const ref = { current: null };
    const gen = vi.fn(() => 'abc-123');
    expect(ensureKey(ref, gen)).toBe('abc-123');
    expect(ensureKey(ref, gen)).toBe('abc-123');
    expect(ensureKey(ref, gen)).toBe('abc-123');
    expect(gen).toHaveBeenCalledTimes(1);
  });

  it('resetKey + ensureKey — fresh key after reset', () => {
    const ref = { current: null };
    const gen = vi.fn().mockReturnValueOnce('first').mockReturnValueOnce('second');
    expect(ensureKey(ref, gen)).toBe('first');
    resetKey(ref);
    expect(ref.current).toBeNull();
    expect(ensureKey(ref, gen)).toBe('second');
  });

  it('safeUUID — UUID-shape string', () => {
    const uuid = safeUUID();
    expect(typeof uuid).toBe('string');
    expect(uuid).toMatch(/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i);
  });

  it('ensureKey — uses safeUUID by default', () => {
    const ref = { current: null };
    const key = ensureKey(ref);
    expect(typeof key).toBe('string');
    expect(key.length).toBeGreaterThan(0);
  });

  it('ensureKey — null-safe', () => {
    expect(ensureKey(null)).toBeNull();
    expect(ensureKey(undefined)).toBeNull();
  });
});
