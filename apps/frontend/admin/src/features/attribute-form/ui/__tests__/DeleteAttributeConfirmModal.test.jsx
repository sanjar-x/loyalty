/**
 * Audit 8.2 — verify the blocked-warning and submit-error blocks no
 * longer race for the same `role="alert"` channel. Pre-fix both
 * carried role="alert" simultaneously, so SR users heard the same
 * "deletion blocked" assertion twice for one user state.
 */
import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { DeleteAttributeConfirmModal } from '../DeleteAttributeConfirmModal';

vi.mock('@/entities/attribute', () => ({
  useAttributeUsage: vi.fn(),
  useDeleteAttribute: () => ({
    mutate: vi.fn(),
    mutateAsync: vi.fn(),
    reset: vi.fn(),
    isPending: false,
  }),
}));

import { useAttributeUsage } from '@/entities/attribute';

function wrap(node) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return <QueryClientProvider client={client}>{node}</QueryClientProvider>;
}

const ATTR = {
  id: 'a1',
  code: 'color',
  nameI18N: { ru: 'Цвет', en: 'Color' },
};

describe('<DeleteAttributeConfirmModal>', () => {
  it('blocked state uses role="status", not role="alert"', () => {
    useAttributeUsage.mockReturnValue({
      data: {
        templateCount: 1,
        templates: [],
        categoryCount: 0,
        categories: [],
        productCount: 0,
      },
      isPending: false,
    });

    render(wrap(<DeleteAttributeConfirmModal open attribute={ATTR} />));

    // Blocked notice is informational — must NOT carry role="alert".
    const status = screen.getByRole('status');
    expect(status).toHaveTextContent(/Атрибут используется/);

    // No alert in the blocked-only state — the submit error hasn't
    // been triggered yet, so the assertive channel must stay silent.
    expect(screen.queryByRole('alert')).toBeNull();
  });

  it('renders no blocked notice when usage is zero', () => {
    useAttributeUsage.mockReturnValue({
      data: {
        templateCount: 0,
        templates: [],
        categoryCount: 0,
        categories: [],
        productCount: 0,
      },
      isPending: false,
    });

    render(wrap(<DeleteAttributeConfirmModal open attribute={ATTR} />));
    expect(screen.queryByRole('status')).toBeNull();
    expect(screen.queryByRole('alert')).toBeNull();
  });
});
