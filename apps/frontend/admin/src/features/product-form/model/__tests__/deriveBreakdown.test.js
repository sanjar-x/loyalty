/**
 * Backend PR #79 (2026-05-12) supersedes the reverted PR #78
 * `componentsBreakdown` with `bindings: FormulaBindingValue[]`. Verify
 * both code paths (new `bindings` list, legacy `components` dict) plus
 * the `isVisible` filter and `componentTag === 'final_price'` semantics.
 *
 * Internal row shape `{code, name, value, displayValue, isFinal}` is
 * what the price-card expander iterates over and must stay stable as
 * the backend wire format evolves.
 */
import { describe, expect, it } from 'vitest';
import { deriveBreakdown } from '../useSellingPricePreview';

describe('deriveBreakdown', () => {
  it('returns [] when preview is empty / missing', () => {
    expect(deriveBreakdown(null)).toEqual([]);
    expect(deriveBreakdown({})).toEqual([]);
  });

  it('prefers PR #79 bindings list when present', () => {
    const rows = deriveBreakdown({
      finalPrice: '7156.75',
      currency: 'RUB',
      components: { ignored_legacy: '999' },
      bindings: [
        {
          name: 'tsena_v_rublyakh',
          componentTag: 'intermediate',
          label: 'Цена в рублях',
          isVisible: true,
          value: '6756.75',
        },
        {
          name: 'itogovaya_sebestoimost',
          componentTag: 'intermediate',
          label: 'Итоговая себестоимость',
          isVisible: true,
          value: '7156.75',
        },
        {
          name: 'final_price',
          componentTag: 'final_price',
          label: 'Итоговая цена',
          isVisible: true,
          value: '7156.75',
        },
      ],
    });
    expect(rows).toHaveLength(3);
    expect(rows[0]).toMatchObject({
      code: 'tsena_v_rublyakh',
      name: 'Цена в рублях',
      isFinal: false,
    });
    // Legacy dict is ignored when the list is present.
    expect(rows.some((r) => r.code === 'ignored_legacy')).toBe(false);
    // Final row inferred from componentTag, not from value match.
    expect(rows.at(-1)).toMatchObject({
      code: 'final_price',
      name: 'Итоговая цена',
      isFinal: true,
    });
    expect(rows.at(-1).displayValue).toMatch(/7\s?156/);
    expect(rows.at(-1).displayValue).toContain('₽');
  });

  it('drops bindings with isVisible === false', () => {
    const rows = deriveBreakdown({
      finalPrice: '100',
      bindings: [
        {
          name: 'private_step',
          componentTag: 'intermediate',
          label: 'Скрытый шаг',
          isVisible: false,
          value: '50',
        },
        {
          name: 'final_price',
          componentTag: 'final_price',
          label: 'Итог',
          isVisible: true,
          value: '100',
        },
      ],
    });
    expect(rows.map((r) => r.code)).toEqual(['final_price']);
  });

  it('falls back to humanise(name) when binding.label is null', () => {
    const [row] = deriveBreakdown({
      finalPrice: '1',
      bindings: [
        {
          name: 'tsena_za_dostavku_cn_ru',
          componentTag: 'intermediate',
          label: null,
          isVisible: true,
          value: '1',
        },
      ],
    });
    expect(row.name).toBe('Tsena za dostavku cn ru');
  });

  it('does NOT mark a row final just because its value matches finalPrice', () => {
    // Backend may emit several bindings sharing the same value as
    // finalPrice (the example formula does — final_price and
    // itogovaya_sebestoimost both equal 7156.75). Only componentTag
    // can decide the final row.
    const rows = deriveBreakdown({
      finalPrice: '7156.75',
      bindings: [
        {
          name: 'itogovaya_sebestoimost',
          componentTag: 'intermediate',
          label: 'Итоговая себестоимость',
          isVisible: true,
          value: '7156.75',
        },
        {
          name: 'final_price',
          componentTag: 'final_price',
          label: 'Итоговая цена',
          isVisible: true,
          value: '7156.75',
        },
      ],
    });
    expect(rows[0].isFinal).toBe(false);
    expect(rows[1].isFinal).toBe(true);
  });

  it('falls back to the legacy components dict when bindings is absent', () => {
    const rows = deriveBreakdown({
      finalPrice: '500.00',
      currency: 'RUB',
      components: {
        base_price: '400.00',
        final_price: '500.00',
      },
    });
    expect(rows).toHaveLength(2);
    expect(rows.map((r) => r.code).sort()).toEqual([
      'base_price',
      'final_price',
    ]);
    // Best-effort isFinal: matches the row whose value equals finalPrice.
    const finalRow = rows.find((r) => r.code === 'final_price');
    expect(finalRow.isFinal).toBe(true);
    const baseRow = rows.find((r) => r.code === 'base_price');
    expect(baseRow.isFinal).toBe(false);
  });
});
