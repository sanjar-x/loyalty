import { describe, expect, it } from 'vitest';
import {
  cn,
  formatCurrency,
  pluralizeRu,
  i18n,
  buildI18nPayload,
  buildFacetOptions,
} from '../utils';

describe('cn', () => {
  it('merges Tailwind classes and resolves conflicts via twMerge', () => {
    expect(cn('px-2 py-1', 'px-4')).toBe('py-1 px-4');
  });

  it('handles falsy values gracefully', () => {
    expect(cn('text-sm', false, null, undefined, 'font-bold')).toBe(
      'text-sm font-bold',
    );
  });
});

describe('formatCurrency', () => {
  it('formats integer rubles with non-breaking space and ₽ symbol', () => {
    expect(formatCurrency(12990)).toMatch(/12\s990\s₽/);
  });

  it('falls back to 0 ₽ for invalid input', () => {
    expect(formatCurrency('not-a-number')).toMatch(/0\s₽/);
  });
});

describe('pluralizeRu', () => {
  it('chooses correct form for each numeric grouping', () => {
    expect(pluralizeRu(1, 'товар', 'товара', 'товаров')).toBe('товар');
    expect(pluralizeRu(2, 'товар', 'товара', 'товаров')).toBe('товара');
    expect(pluralizeRu(5, 'товар', 'товара', 'товаров')).toBe('товаров');
    expect(pluralizeRu(11, 'товар', 'товара', 'товаров')).toBe('товаров');
    expect(pluralizeRu(21, 'товар', 'товара', 'товаров')).toBe('товар');
  });
});

describe('i18n', () => {
  it('prefers ru, falls back to en, then to first value, then to fallback', () => {
    expect(i18n({ ru: 'Привет', en: 'Hello' })).toBe('Привет');
    expect(i18n({ en: 'Hello' })).toBe('Hello');
    expect(i18n({ uz: 'Salom' })).toBe('Salom');
    expect(i18n(null, 'default')).toBe('default');
    expect(i18n(undefined, 'default')).toBe('default');
  });
});

describe('buildI18nPayload', () => {
  it('copies ru into en when en is empty', () => {
    expect(buildI18nPayload('Кроссовки', '')).toEqual({
      ru: 'Кроссовки',
      en: 'Кроссовки',
    });
  });

  it('keeps both locales when en is provided', () => {
    expect(buildI18nPayload('Кроссовки', 'Sneakers')).toEqual({
      ru: 'Кроссовки',
      en: 'Sneakers',
    });
  });
});

describe('buildFacetOptions', () => {
  it('counts occurrences and prepends "all" option', () => {
    const items = [{ b: 'A' }, { b: 'A' }, { b: 'B' }];
    const { options } = buildFacetOptions(items, (i) => i.b);
    expect(options[0]).toEqual({ value: 'all', label: 'Все', count: 3 });
    expect(options.find((o) => o.value === 'A').count).toBe(2);
    expect(options.find((o) => o.value === 'B').count).toBe(1);
  });
});
