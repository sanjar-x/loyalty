/**
 * Reducer-level test for `MERGE_SKU_PRICING_EVENT` (post-CAT-014 review #5 +
 * the `??`-clearing fix from #4).
 *
 * The reducer is internal to `useProductForm`, so we drive it via the public
 * hook surface: render the hook, hydrate from a fake server snapshot, fire
 * `mergeSkuPricingEvent`, and inspect the resulting state.
 */
import { renderHook, act } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import useProductForm from '../useProductForm';

function makeProduct({ skus }) {
  return {
    id: 'p-1',
    titleI18N: { ru: 'Test', en: 'Test' },
    slug: 'test',
    brandId: 'b-1',
    primaryCategoryId: 'c-1',
    version: 1,
    status: 'draft',
    attributes: [],
    variants: [
      {
        id: 'v-1',
        nameI18n: { ru: 'V1', en: 'V1' },
        skus: skus.slice(0, Math.ceil(skus.length / 2)),
      },
      {
        id: 'v-2',
        nameI18n: { ru: 'V2', en: 'V2' },
        skus: skus.slice(Math.ceil(skus.length / 2)),
      },
    ],
  };
}

const SKU = (id, extras = {}) => ({
  id,
  skuCode: id.toUpperCase(),
  version: 1,
  isActive: true,
  variantAttributes: [],
  price: null,
  purchasePrice: { amount: 80000, currency: 'CNY' },
  sellingPrice: null,
  pricingStatus: 'pending',
  pricedAt: null,
  pricedFailureReason: null,
  ...extras,
});

describe('MERGE_SKU_PRICING_EVENT reducer', () => {
  it('merges fields onto the matching SKU and leaves the rest of the state alone', () => {
    const product = makeProduct({
      skus: [SKU('s-1'), SKU('s-2'), SKU('s-3'), SKU('s-4')],
    });
    const { result } = renderHook(() => useProductForm());
    act(() => result.current.hydrateFromProduct(product, []));

    act(() =>
      result.current.mergeSkuPricingEvent({
        skuId: 's-3',
        pricingStatus: 'priced',
        sellingPrice: { amount: 1290000, currency: 'RUB' },
        pricedAt: '2026-05-08T15:30:00Z',
        pricedFailureReason: null,
      }),
    );

    const allSkus = result.current.state.variants.flatMap((v) => v.skus);
    const target = allSkus.find((s) => s.id === 's-3');
    expect(target.pricingStatus).toBe('priced');
    expect(target.sellingPrice).toEqual({ amount: 1290000, currency: 'RUB' });
    expect(target.pricedAt).toBe('2026-05-08T15:30:00Z');

    // Other SKUs untouched
    const others = allSkus.filter((s) => s.id !== 's-3');
    for (const o of others) expect(o.pricingStatus).toBe('pending');
  });

  it('preserves variant identity when no SKU in that variant matched (touched-flag is per-variant)', () => {
    const product = makeProduct({
      skus: [SKU('s-1'), SKU('s-2'), SKU('s-3'), SKU('s-4')],
    });
    const { result } = renderHook(() => useProductForm());
    act(() => result.current.hydrateFromProduct(product, []));

    const before = result.current.state.variants;
    act(() =>
      result.current.mergeSkuPricingEvent({
        skuId: 's-1', // first variant only
        pricingStatus: 'priced',
      }),
    );
    const after = result.current.state.variants;

    // Variant 0 changes identity (matched), variant 1 must keep its reference
    // — otherwise React.memo / effect deps downstream get spurious work.
    expect(after[0]).not.toBe(before[0]);
    expect(after[1]).toBe(before[1]);
  });

  it('clears `pricedFailureReason` to null when backend recovers from a failure (no `??`-collapse)', () => {
    const product = makeProduct({
      skus: [
        SKU('s-1', {
          pricingStatus: 'formula_error',
          pricedFailureReason: 'Variable {fx_cny_rub} not bound',
          pricedAt: '2026-05-08T10:00:00Z',
        }),
      ],
    });
    const { result } = renderHook(() => useProductForm());
    act(() => result.current.hydrateFromProduct(product, []));

    act(() =>
      result.current.mergeSkuPricingEvent({
        skuId: 's-1',
        pricingStatus: 'priced',
        sellingPrice: { amount: 1000000, currency: 'RUB' },
        pricedAt: '2026-05-08T16:00:00Z',
        pricedFailureReason: null, // <-- explicit clear
      }),
    );

    const target = result.current.state.variants
      .flatMap((v) => v.skus)
      .find((s) => s.id === 's-1');
    expect(target.pricedFailureReason).toBe(null);
    expect(target.pricedAt).toBe('2026-05-08T16:00:00Z');
    expect(target.pricingStatus).toBe('priced');
  });

  it('drops events targeting a SKU that does not exist in state (no crash, no spurious identity churn)', () => {
    const product = makeProduct({ skus: [SKU('s-1'), SKU('s-2')] });
    const { result } = renderHook(() => useProductForm());
    act(() => result.current.hydrateFromProduct(product, []));

    const before = result.current.state;
    act(() =>
      result.current.mergeSkuPricingEvent({
        skuId: 's-unknown',
        pricingStatus: 'priced',
      }),
    );
    expect(result.current.state).toBe(before);
  });

  it('ignores events without a skuId', () => {
    const product = makeProduct({ skus: [SKU('s-1')] });
    const { result } = renderHook(() => useProductForm());
    act(() => result.current.hydrateFromProduct(product, []));

    const before = result.current.state;
    act(() => result.current.mergeSkuPricingEvent({ pricingStatus: 'priced' }));
    expect(result.current.state).toBe(before);
  });

  it('clears `pricingStatus` to null when backend explicitly resets it (uses !== undefined, not ??)', () => {
    const product = makeProduct({
      skus: [SKU('s-1', { pricingStatus: 'formula_error' })],
    });
    const { result } = renderHook(() => useProductForm());
    act(() => result.current.hydrateFromProduct(product, []));

    act(() =>
      result.current.mergeSkuPricingEvent({
        skuId: 's-1',
        pricingStatus: null,
        pricedFailureReason: null,
      }),
    );

    const target = result.current.state.variants
      .flatMap((v) => v.skus)
      .find((s) => s.id === 's-1');
    expect(target.pricingStatus).toBeNull();
  });
});
