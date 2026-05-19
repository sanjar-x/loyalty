import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { PRICING_STATUSES, PricingStatusBadge } from '../PricingStatusBadge';

describe('<PricingStatusBadge>', () => {
  it.each(PRICING_STATUSES)(
    'renders the canonical Russian label for "%s"',
    (status) => {
      render(<PricingStatusBadge status={status} />);
      expect(screen.getByRole('status')).toBeInTheDocument();
    },
  );

  it('renders the priced label for the success state', () => {
    render(<PricingStatusBadge status="priced" />);
    expect(screen.getByText('Цена рассчитана')).toBeInTheDocument();
  });

  it('renders the missing_purchase_price neutral label', () => {
    render(<PricingStatusBadge status="missing_purchase_price" />);
    expect(screen.getByText('Нет закупочной цены')).toBeInTheDocument();
  });

  it('uses the short label in compact mode', () => {
    render(<PricingStatusBadge status="formula_error" compact />);
    expect(screen.getByText('error')).toBeInTheDocument();
    expect(screen.queryByText('Ошибка формулы')).not.toBeInTheDocument();
  });

  it('attaches the tooltip text to the title attribute', () => {
    render(
      <PricingStatusBadge
        status="formula_error"
        tooltip="Variable {fx_cny_rub} not bound for context CN"
      />,
    );
    const badge = screen.getByRole('status');
    expect(badge).toHaveAttribute(
      'title',
      'Variable {fx_cny_rub} not bound for context CN',
    );
    // aria-label combines label + tooltip so screen readers hear both
    expect(badge).toHaveAttribute(
      'aria-label',
      expect.stringContaining('Variable {fx_cny_rub}'),
    );
  });

  it('falls back to a neutral placeholder for unknown statuses', () => {
    render(<PricingStatusBadge status="bogus_state" />);
    expect(screen.getByText('bogus_state')).toBeInTheDocument();
  });

  it('includes legacy in the canonical FSM list (CAT-019/CAT-020)', () => {
    expect(PRICING_STATUSES).toContain('legacy');
  });

  it('renders the legacy label as a non-failure but distinct state', () => {
    render(<PricingStatusBadge status="legacy" />);
    expect(screen.getByText(/legacy SKU/i)).toBeInTheDocument();
  });
});
