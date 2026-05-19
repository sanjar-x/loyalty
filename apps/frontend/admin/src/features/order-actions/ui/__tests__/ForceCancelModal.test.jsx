/**
 * Integration tests for <ForceCancelModal>: locks the post-D0.1
 * grouped CancellationReason picker (categories from the backend
 * `_meta/cancellation-reasons` taxonomy, served via BFF
 * `/api/admin/orders/meta/cancellation-reasons`) + search +
 * idempotencyKey freezing.
 *
 * The reasons taxonomy is seeded directly into the QueryClient via
 * `setQueryData(orderKeys.meta('cancellation-reasons'), ...)` so the
 * picker renders synchronously without racing the BFF fetch. The
 * force-cancel POST itself is stubbed via `global.fetch` so the
 * mutation captures the body the user submitted.
 */
import { afterEach, describe, expect, it, vi } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import {
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from '@testing-library/react';

import { orderKeys } from '@/entities/order';

import { ForceCancelModal } from '../ForceCancelModal';

const ORDER = {
  orderId: '019cdbf4-e987-7000-8080-000000000001',
  status: 'paid',
  paymentIntentId: 'pi-1',
};

const META_RESPONSE = {
  categories: [
    {
      code: 'customer',
      reasons: ['customer_changed_mind', 'customer_found_better_price'],
    },
    {
      code: 'merchant',
      reasons: ['merchant_out_of_stock', 'merchant_price_error'],
    },
    { code: 'system', reasons: ['system_payment_failed'] },
    { code: 'logistics', reasons: ['logistics_customs_rejected'] },
  ],
};

function makeWrapper({ withMeta = true } = {}) {
  const client = new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: Infinity, staleTime: Infinity },
      mutations: { retry: false },
    },
  });
  if (withMeta) {
    client.setQueryData(orderKeys.meta('cancellation-reasons'), META_RESPONSE);
  }
  function Wrapper({ children }) {
    return (
      <QueryClientProvider client={client}>{children}</QueryClientProvider>
    );
  }
  return { client, Wrapper };
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe('<ForceCancelModal>', () => {
  it('renders a grouped picker with category headers + ru reason labels', async () => {
    const { Wrapper } = makeWrapper();
    render(<ForceCancelModal open onClose={vi.fn()} order={ORDER} />, {
      wrapper: Wrapper,
    });

    // testing-library's accessible-name resolution fights with the
    // ▾ glyph in the trigger; getElementById sidesteps that and is
    // safe because the trigger has a stable, non-arbitrary id.
    fireEvent.click(document.getElementById('cancel-reason-trigger'));

    const listbox = await screen.findByRole('listbox', {
      name: /Причины отмены/,
    });
    expect(within(listbox).getByText('От покупателя')).toBeInTheDocument();
    expect(within(listbox).getByText('От продавца')).toBeInTheDocument();
    expect(within(listbox).getByText('Системное')).toBeInTheDocument();
    expect(within(listbox).getByText('Логистическое')).toBeInTheDocument();
    expect(within(listbox).getByText('Передумал')).toBeInTheDocument();
  });

  it('filters by ru label and by enum code', async () => {
    const { Wrapper } = makeWrapper();
    render(<ForceCancelModal open onClose={vi.fn()} order={ORDER} />, {
      wrapper: Wrapper,
    });

    fireEvent.click(document.getElementById('cancel-reason-trigger'));
    await screen.findByRole('listbox', { name: /Причины отмены/ });

    const search = screen.getByLabelText('Поиск причины отмены');

    fireEvent.change(search, { target: { value: 'переду' } });
    expect(screen.getByText('Передумал')).toBeInTheDocument();
    expect(screen.queryByText('Нет в наличии')).not.toBeInTheDocument();

    fireEvent.change(search, { target: { value: 'merchant' } });
    expect(screen.getByText('Нет в наличии')).toBeInTheDocument();
    expect(screen.queryByText('Передумал')).not.toBeInTheDocument();
  });

  it('submits the chosen enum code + a frozen idempotencyKey', async () => {
    const onClose = vi.fn();
    const fetchSpy = vi.fn(() =>
      Promise.resolve(new Response(null, { status: 204 })),
    );
    vi.stubGlobal('fetch', fetchSpy);

    const { Wrapper } = makeWrapper();
    render(<ForceCancelModal open onClose={onClose} order={ORDER} />, {
      wrapper: Wrapper,
    });

    fireEvent.click(document.getElementById('cancel-reason-trigger'));
    await screen.findByRole('listbox', { name: /Причины отмены/ });

    fireEvent.click(screen.getByText('Передумал'));
    fireEvent.click(
      screen.getByRole('button', { name: /Принудительная отмена/ }),
    );

    await waitFor(() => expect(onClose).toHaveBeenCalled());

    const cancelCall = fetchSpy.mock.calls.find(([url]) =>
      String(url).includes('/force-cancel'),
    );
    expect(cancelCall).toBeDefined();
    const body = JSON.parse(cancelCall[1].body);
    expect(body.reason).toBe('customer_changed_mind');
    expect(typeof body.idempotencyKey).toBe('string');
    expect(body.idempotencyKey.length).toBeGreaterThanOrEqual(8);
  });

  it('shows the wasPaid warning banner when paymentIntentId is set', () => {
    const { Wrapper } = makeWrapper();
    render(<ForceCancelModal open onClose={vi.fn()} order={ORDER} />, {
      wrapper: Wrapper,
    });

    expect(screen.getByRole('alert')).toHaveTextContent(/возврат средств/);
  });
});
