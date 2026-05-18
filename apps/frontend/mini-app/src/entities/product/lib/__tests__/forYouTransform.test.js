import { describe, it, expect } from 'vitest';

import { transformForYouFeed } from '../transformers';

/**
 * Regression guard — the `getForYouFeed` transformResponse accepts both
 * backend snake_case (`next_cursor`, `strategy_version`, `is_personalized`)
 * and camelCase. The real backend currently sends snake_case; reading only
 * the camelCase variant of `?.nextCursor` in transformResponse used to
 * cause the "For You" feed to appear empty.
 */
describe('transformForYouFeed — snake_case ↔ camelCase tolerance', () => {
  it('snake_case real backend response', () => {
    const out = transformForYouFeed({
      items: [],
      next_cursor: 'abc123',
      strategy_version: 'v2',
      is_personalized: true,
    });
    expect(out.nextCursor).toBe('abc123');
    expect(out.hasNext).toBe(true);
    expect(out.strategyVersion).toBe('v2');
    expect(out.isPersonalized).toBe(true);
  });

  it('camelCase response — updated in the future', () => {
    const out = transformForYouFeed({
      items: [],
      nextCursor: 'xyz',
      strategyVersion: 'v3',
      isPersonalized: true,
    });
    expect(out.nextCursor).toBe('xyz');
    expect(out.hasNext).toBe(true);
    expect(out.strategyVersion).toBe('v3');
    expect(out.isPersonalized).toBe(true);
  });

  it('empty body — hasNext=false, isPersonalized=false', () => {
    const out = transformForYouFeed({});
    expect(out.nextCursor).toBeNull();
    expect(out.hasNext).toBe(false);
    expect(out.isPersonalized).toBe(false);
    expect(out.items).toEqual([]);
  });

  it('null/undefined response — does not crash', () => {
    const a = transformForYouFeed(null);
    expect(a.items).toEqual([]);
    expect(a.hasNext).toBe(false);

    const b = transformForYouFeed(undefined);
    expect(b.nextCursor).toBeNull();
  });

  it('when both camelCase and snake_case are present — camelCase wins', () => {
    const out = transformForYouFeed({
      nextCursor: 'newer',
      next_cursor: 'older',
    });
    expect(out.nextCursor).toBe('newer');
  });
});
