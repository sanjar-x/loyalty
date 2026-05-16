import { describe, it, expect } from 'vitest';

import { transformForYouFeed } from '../transformers';

/**
 * Regression guard — `getForYouFeed` transformResponse'i backend
 * snake_case (`next_cursor`, `strategy_version`, `is_personalized`)
 * va camelCase'ni ikkalasini qabul qiladi. Real backend hozir
 * snake_case yuboradi; transformResponse'da `?.nextCursor`'ni faqat
 * camelCase variantida o'qish "Для вас" feed'ni boshqarib bo'sh
 * ko'rinishiga sabab bo'lgan edi.
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

  it('camelCase response — kelajakda yangilangan', () => {
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

  it('null/undefined response — krash bermaydi', () => {
    const a = transformForYouFeed(null);
    expect(a.items).toEqual([]);
    expect(a.hasNext).toBe(false);

    const b = transformForYouFeed(undefined);
    expect(b.nextCursor).toBeNull();
  });

  it("camelCase ham, snake_case ham bo'lsa — camelCase ustun", () => {
    const out = transformForYouFeed({
      nextCursor: 'newer',
      next_cursor: 'older',
    });
    expect(out.nextCursor).toBe('newer');
  });
});
