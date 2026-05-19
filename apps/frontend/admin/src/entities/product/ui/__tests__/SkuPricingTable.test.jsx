/**
 * Regression tests for <SkuPricingTable> — read-only view surfaced on the
 * product detail page (CAT-004 Part 1). Exercises the response-shape mapping
 * for the CAT-003 pricing fields without coupling to the live SSE stream
 * (that's covered by the hook tests).
 */
import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { SkuPricingTable } from '../SkuPricingTable';

const SKU_PRICED = {
  id: 'sku-1',
  skuCode: 'AM90-BLK-42',
  variantAttributes: [
    {
      attributeId: 'a-color',
      attributeValueId: 'v-black',
      attributeValueCode: 'black',
      attributeValueNameI18N: { ru: 'Чёрный', en: 'Black' },
    },
    {
      attributeId: 'a-size',
      attributeValueId: 'v-42',
      attributeValueCode: '42',
      attributeValueNameI18N: { ru: '42', en: '42' },
    },
  ],
  price: { amount: 1_290_000, currency: 'RUB' },
  purchasePrice: { amount: 80_000, currency: 'CNY' },
  sellingPrice: { amount: 1_290_000, currency: 'RUB' },
  pricingStatus: 'priced',
  pricedAt: '2026-05-08T09:30:00Z',
  pricedFailureReason: null,
};

const SKU_FAILED = {
  ...SKU_PRICED,
  id: 'sku-2',
  skuCode: 'AM90-BLK-43',
  pricingStatus: 'formula_error',
  pricedFailureReason: 'Variable {fx_cny_rub} not bound for pricing context CN',
  sellingPrice: null,
  pricedAt: '2026-05-08T09:31:00Z',
};

const SKU_MISSING = {
  ...SKU_PRICED,
  id: 'sku-3',
  skuCode: 'AM90-BLK-44',
  purchasePrice: null,
  sellingPrice: null,
  pricingStatus: 'missing_purchase_price',
  pricedAt: null,
};

describe('<SkuPricingTable>', () => {
  it('renders an empty hint when no SKUs are provided', () => {
    render(<SkuPricingTable skus={[]} />);
    expect(screen.getByText(/Нет SKU/)).toBeInTheDocument();
  });

  it('renders the SKU code, attributes, and money columns for a priced SKU', () => {
    render(<SkuPricingTable skus={[SKU_PRICED]} />);
    expect(screen.getByText('AM90-BLK-42')).toBeInTheDocument();
    expect(screen.getByText('Чёрный / 42')).toBeInTheDocument();
    // 1_290_000 kopecks = 12 900 RUB; the formatter uses NBSP — match by digits only
    const rows = screen.getAllByText(/12\D?900\s+₽/);
    // price + sellingPrice both render the same formatted value
    expect(rows.length).toBeGreaterThanOrEqual(2);
    expect(screen.getByText(/¥\s+800/)).toBeInTheDocument();
  });

  it('renders the formula_error badge with the failure reason as tooltip', () => {
    render(<SkuPricingTable skus={[SKU_FAILED]} />);
    const badge = screen.getByRole('status');
    expect(badge).toHaveAttribute(
      'title',
      'Variable {fx_cny_rub} not bound for pricing context CN',
    );
  });

  it('renders an em-dash when money fields and pricedAt are null', () => {
    render(<SkuPricingTable skus={[SKU_MISSING]} />);
    // multiple — placeholders: purchasePrice, sellingPrice, pricedAt
    const dashes = screen.getAllByText('—');
    expect(dashes.length).toBeGreaterThanOrEqual(3);
  });

  it('falls back to missing_purchase_price when pricingStatus is undefined', () => {
    const skuWithoutStatus = { ...SKU_PRICED, pricingStatus: undefined };
    render(<SkuPricingTable skus={[skuWithoutStatus]} />);
    const badge = screen.getByRole('status');
    expect(badge).toHaveAttribute('title', 'Нет закупочной цены');
  });
});
