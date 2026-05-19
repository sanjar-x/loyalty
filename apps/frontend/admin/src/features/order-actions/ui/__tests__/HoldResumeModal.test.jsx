/**
 * Integration tests for <HoldResumeModal>: pin the post-D0.1 typed
 * HoldReason picker (radiogroup of 4 admin-pickable values) and the
 * resume-mode short-circuit. Backend mutation hits the BFF — we stub
 * `global.fetch` with a 204 to keep the test pure.
 */
import { afterEach, describe, expect, it, vi } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';

import { HOLD_REASONS_FOR_ADMIN } from '@/entities/order';
import { HoldResumeModal } from '../HoldResumeModal';

const ORDER = {
  orderId: '019cdbf4-e987-7000-8080-000000000001',
  status: 'paid',
  preHoldStatus: null,
};

function makeWrapper() {
  const client = new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: Infinity, staleTime: 0 },
      mutations: { retry: false },
    },
  });
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

describe('<HoldResumeModal>', () => {
  it('renders one radio per admin-pickable HoldReason', () => {
    const { Wrapper } = makeWrapper();
    render(
      <HoldResumeModal open onClose={vi.fn()} order={ORDER} mode="hold" />,
      { wrapper: Wrapper },
    );

    const radios = screen.getAllByRole('radio');
    expect(radios).toHaveLength(HOLD_REASONS_FOR_ADMIN.length);
    expect(HOLD_REASONS_FOR_ADMIN).not.toContain('booking_failed');
  });

  it('disables submit until a reason is picked, then sends enum value', async () => {
    const onClose = vi.fn();
    const fetchSpy = vi.fn(() =>
      Promise.resolve(new Response(null, { status: 204 })),
    );
    vi.stubGlobal('fetch', fetchSpy);

    const { Wrapper } = makeWrapper();
    render(
      <HoldResumeModal open onClose={onClose} order={ORDER} mode="hold" />,
      { wrapper: Wrapper },
    );

    const submit = screen.getByRole('button', { name: /Поставить на hold/ });
    expect(submit).toBeDisabled();

    fireEvent.click(screen.getByRole('radio', { name: /Паспорт не прошёл/ }));
    expect(submit).not.toBeDisabled();

    fireEvent.click(submit);

    await waitFor(() => expect(onClose).toHaveBeenCalled());

    const [, init] = fetchSpy.mock.calls.at(-1);
    expect(JSON.parse(init.body)).toEqual({ reason: 'passport_invalid' });
  });

  it('resume mode skips the radio group and sends an empty body', async () => {
    const onClose = vi.fn();
    const fetchSpy = vi.fn(() =>
      Promise.resolve(new Response(null, { status: 204 })),
    );
    vi.stubGlobal('fetch', fetchSpy);

    const { Wrapper } = makeWrapper();
    render(
      <HoldResumeModal
        open
        onClose={onClose}
        order={{ ...ORDER, status: 'on_hold', preHoldStatus: 'paid' }}
        mode="resume"
      />,
      { wrapper: Wrapper },
    );

    expect(screen.queryByRole('radiogroup')).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /Возобновить/ }));

    await waitFor(() => expect(onClose).toHaveBeenCalled());
    const [, init] = fetchSpy.mock.calls.at(-1);
    expect(init.body).toBeUndefined();
  });
});
