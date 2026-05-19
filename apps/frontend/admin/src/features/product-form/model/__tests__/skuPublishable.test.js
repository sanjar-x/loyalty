/**
 * Unit tests for `skuPublishable` (CAT-012).
 *
 * The helper drives the publish gate on the product detail page and the
 * publish-button enablement inside <ProductDetailsForm> in edit mode. Mirrors
 * the backend rule (CAT-009 + CAT-011): a SKU is publishable only when it
 * has either a manual price *or* an autonomous pricing result that has
 * actually landed (`pricingStatus === 'priced'`).
 */
import { describe, expect, it } from 'vitest';

import { skuPublishable } from '@/entities/product';

const PRICED = { amount: 990000, currency: 'RUB' };
const COST = { amount: 80000, currency: 'CNY' };

describe('skuPublishable', () => {
  it('returns false for null/undefined input', () => {
    expect(skuPublishable(null)).toBe(false);
    expect(skuPublishable(undefined)).toBe(false);
  });

  it('returns true when a positive manual price is set, regardless of pricing status', () => {
    expect(skuPublishable({ price: PRICED, pricingStatus: 'pending' })).toBe(
      true,
    );
    expect(
      skuPublishable({ price: PRICED, pricingStatus: 'formula_error' }),
    ).toBe(true);
    expect(skuPublishable({ price: PRICED })).toBe(true);
  });

  it('returns false when only purchasePrice is set and the recompute is still pending', () => {
    expect(
      skuPublishable({ purchasePrice: COST, pricingStatus: 'pending' }),
    ).toBe(false);
  });

  it('returns true when purchasePrice is set and the recompute has landed (priced)', () => {
    expect(
      skuPublishable({ purchasePrice: COST, pricingStatus: 'priced' }),
    ).toBe(true);
  });

  it('returns false when the recompute failed (formula_error / stale_fx / missing)', () => {
    for (const status of [
      'formula_error',
      'stale_fx',
      'missing_purchase_price',
    ]) {
      expect(
        skuPublishable({ purchasePrice: COST, pricingStatus: status }),
      ).toBe(false);
    }
  });

  it('returns false when neither price nor purchasePrice is set', () => {
    expect(skuPublishable({})).toBe(false);
    expect(skuPublishable({ pricingStatus: 'priced' })).toBe(false);
  });

  it('treats zero amount as missing (price 0 does not count as manual)', () => {
    expect(
      skuPublishable({
        price: { amount: 0, currency: 'RUB' },
        purchasePrice: COST,
        pricingStatus: 'pending',
      }),
    ).toBe(false);
    expect(
      skuPublishable({
        price: { amount: 0, currency: 'RUB' },
        purchasePrice: COST,
        pricingStatus: 'priced',
      }),
    ).toBe(true);
  });
});
