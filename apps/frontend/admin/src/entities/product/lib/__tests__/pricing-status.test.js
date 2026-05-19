/**
 * Pure-logic tests for pricing-status helpers (post-CAT-014 review).
 *
 * `skuPublishable` is also covered from the form-side at
 * `features/product-form/model/__tests__/skuPublishable.test.js`; this file
 * focuses on `computePublishGate` since it's the function the publish bar
 * consumes.
 */
import { describe, expect, it } from 'vitest';

import { PRICING_FAILURE_STATUSES, computePublishGate } from '../pricingStatus';

const PRICED_RUB = { amount: 990000, currency: 'RUB' };
const COST_CNY = { amount: 80000, currency: 'CNY' };

describe('PRICING_FAILURE_STATUSES', () => {
  it('contains the three blocking states from the backend FSM', () => {
    expect(PRICING_FAILURE_STATUSES).toEqual(
      expect.arrayContaining([
        'formula_error',
        'stale_fx',
        'missing_purchase_price',
      ]),
    );
  });
});

describe('computePublishGate', () => {
  it('returns unblocked for an empty SKU set (caller decides what that means)', () => {
    expect(computePublishGate([])).toEqual({ blocked: false, reason: null });
  });

  it('unblocks when every SKU has a manual price', () => {
    const result = computePublishGate([
      { id: 'a', price: PRICED_RUB },
      { id: 'b', price: PRICED_RUB },
    ]);
    expect(result.blocked).toBe(false);
  });

  it('unblocks when every SKU is on the autonomous path with `priced` status', () => {
    const result = computePublishGate([
      { id: 'a', purchasePrice: COST_CNY, pricingStatus: 'priced' },
      { id: 'b', purchasePrice: COST_CNY, pricingStatus: 'priced' },
    ]);
    expect(result.blocked).toBe(false);
  });

  it('blocks while any SKU is still pending recompute (no manual price fallback)', () => {
    const result = computePublishGate([
      { id: 'a', price: PRICED_RUB },
      { id: 'b', purchasePrice: COST_CNY, pricingStatus: 'pending' },
    ]);
    expect(result.blocked).toBe(true);
    expect(result.reason).toMatch(/пересчитываются/);
  });

  it.each(PRICING_FAILURE_STATUSES)(
    'blocks with the failure label when any SKU is in "%s"',
    (status) => {
      const result = computePublishGate([
        { id: 'a', price: PRICED_RUB },
        {
          id: 'b',
          purchasePrice: COST_CNY,
          pricingStatus: status,
          pricedFailureReason: null,
        },
      ]);
      expect(result.blocked).toBe(true);
      expect(result.reason).toBeTruthy();
    },
  );

  it('appends pricedFailureReason to the label when backend supplied one', () => {
    const result = computePublishGate([
      {
        id: 'a',
        purchasePrice: COST_CNY,
        pricingStatus: 'formula_error',
        pricedFailureReason: 'Variable {fx_cny_rub} not bound',
      },
    ]);
    expect(result.reason).toBe(
      'Ошибка формулы: Variable {fx_cny_rub} not bound',
    );
  });

  it('blocks with a "no pricing entered" message when no SKU has price or purchasePrice (post-review fix #6)', () => {
    const result = computePublishGate([
      { id: 'a' },
      { id: 'b', price: null, purchasePrice: null },
    ]);
    expect(result.blocked).toBe(true);
    expect(result.reason).toMatch(/Не задана цена/);
  });

  it('does not trigger the no-pricing branch when at least one SKU has any input', () => {
    const result = computePublishGate([
      { id: 'a' },
      { id: 'b', price: PRICED_RUB },
    ]);
    expect(result.blocked).toBe(false);
  });

  it('failure check takes precedence over the pending check', () => {
    const result = computePublishGate([
      { id: 'a', purchasePrice: COST_CNY, pricingStatus: 'pending' },
      { id: 'b', purchasePrice: COST_CNY, pricingStatus: 'formula_error' },
    ]);
    // Failure dominates — reason mentions formula error, not the pending hint.
    expect(result.blocked).toBe(true);
    expect(result.reason).toMatch(/Ошибка формулы/);
    expect(result.reason).not.toMatch(/пересчитываются/);
  });

  it('blocks legacy SKUs that have not been re-saved through the recompute pipeline', () => {
    const result = computePublishGate([
      { id: 'a', price: PRICED_RUB },
      { id: 'b', pricingStatus: 'legacy' },
    ]);
    expect(result.blocked).toBe(true);
    expect(result.reason).toMatch(/пересчёт/);
  });

  it('failure status still wins over legacy status', () => {
    const result = computePublishGate([
      { id: 'a', pricingStatus: 'legacy' },
      {
        id: 'b',
        purchasePrice: COST_CNY,
        pricingStatus: 'formula_error',
      },
    ]);
    expect(result.blocked).toBe(true);
    expect(result.reason).toMatch(/Ошибка формулы/);
  });
});
