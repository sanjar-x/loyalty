import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { PublishGateBlocker } from '../PublishGateBlocker';

const sample = (overrides = {}) => ({
  skuId: 'sku-1',
  skuCode: 'TSHIRT-M-BLK',
  pricingStatus: 'missing_purchase_price',
  hasManualPrice: false,
  hasSellingPrice: false,
  hasPurchasePrice: false,
  failureReason: null,
  nextStep: 'Set ``purchase_price`` on this SKU.',
  ...overrides,
});

describe('<PublishGateBlocker>', () => {
  it('renders nothing when diagnostics is empty', () => {
    const { container } = render(<PublishGateBlocker diagnostics={[]} />);
    expect(container.firstChild).toBeNull();
  });

  it('renders one row per diagnostic with badge + next step + action', () => {
    render(
      <PublishGateBlocker
        diagnostics={[
          sample(),
          sample({
            skuId: 'sku-2',
            skuCode: 'TSHIRT-L-BLK',
            pricingStatus: 'pending',
            nextStep: 'Wait ~5 seconds for recompute.',
          }),
        ]}
      />,
    );
    expect(screen.getByText('TSHIRT-M-BLK')).toBeInTheDocument();
    expect(screen.getByText('TSHIRT-L-BLK')).toBeInTheDocument();
    expect(
      screen.getByText('Set ``purchase_price`` on this SKU.'),
    ).toBeInTheDocument();
    expect(
      screen.getByText('Wait ~5 seconds for recompute.'),
    ).toBeInTheDocument();
  });

  it('shows a Retry button for pending rows and wires onRetry', async () => {
    const onRetry = vi.fn();
    render(
      <PublishGateBlocker
        diagnostics={[
          sample({ skuId: 'p1', pricingStatus: 'pending', skuCode: 'P-1' }),
        ]}
        onRetry={onRetry}
      />,
    );
    const retry = screen.getByRole('button', { name: /повторить/i });
    await userEvent.click(retry);
    expect(onRetry).toHaveBeenCalledTimes(1);
  });

  it('calls onSetPurchasePrice with skuId for missing_purchase_price rows', async () => {
    const onSet = vi.fn();
    render(
      <PublishGateBlocker
        diagnostics={[sample({ skuId: 'pp-7' })]}
        onSetPurchasePrice={onSet}
      />,
    );
    const button = screen.getByRole('button', { name: /закупочная цена/i });
    await userEvent.click(button);
    expect(onSet).toHaveBeenCalledWith('pp-7');
  });

  it('shows Retry only for pending and Закупочная for cost-missing in the same table', () => {
    render(
      <PublishGateBlocker
        diagnostics={[
          sample({ skuId: 'a', pricingStatus: 'pending', skuCode: 'A' }),
          sample({
            skuId: 'b',
            pricingStatus: 'missing_purchase_price',
            skuCode: 'B',
          }),
        ]}
      />,
    );
    const rows = screen.getAllByRole('row').slice(1); // skip header
    const aRow = rows.find((r) => within(r).queryByText('A'));
    const bRow = rows.find((r) => within(r).queryByText('B'));
    expect(
      within(aRow).getByRole('button', { name: /повторить/i }),
    ).toBeInTheDocument();
    expect(
      within(aRow).queryByRole('button', { name: /закупочная/i }),
    ).toBeNull();
    expect(
      within(bRow).getByRole('button', { name: /закупочная цена/i }),
    ).toBeInTheDocument();
    expect(
      within(bRow).queryByRole('button', { name: /повторить/i }),
    ).toBeNull();
  });

  it('falls back to local next-step hint when backend nextStep is missing', () => {
    render(
      <PublishGateBlocker
        diagnostics={[
          sample({
            skuId: 'l',
            pricingStatus: 'legacy',
            skuCode: 'L',
            nextStep: '',
          }),
        ]}
      />,
    );
    // PRICING_NEXT_STEP_HINTS.legacy
    expect(
      screen.getByText(/пересохраните закупочную цену/i),
    ).toBeInTheDocument();
  });

  it('disables retry button while a transition is in flight', () => {
    render(
      <PublishGateBlocker
        diagnostics={[
          sample({ skuId: 'p', pricingStatus: 'pending', skuCode: 'P' }),
        ]}
        onRetry={vi.fn()}
        retrying
      />,
    );
    expect(screen.getByRole('button', { name: /повтор/i })).toBeDisabled();
  });
});
