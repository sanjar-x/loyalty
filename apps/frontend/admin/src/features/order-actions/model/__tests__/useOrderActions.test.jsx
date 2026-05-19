/**
 * Cache-invalidation regression tests for useOrderActions mutations.
 *
 * For each mutation we want to lock the contract that on success the
 * detail / history / list query keys are invalidated so any open surface
 * picks up the post-transition state. The test stubs `global.fetch` to
 * return a 204 (matches backend) and inspects the QueryClient afterwards.
 */
import { afterEach, describe, expect, it, vi } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { act, renderHook } from '@testing-library/react';

import { orderKeys } from '@/entities/order';

import {
  useChangePickupPoint,
  useForceCancelOrder,
  useHoldOrder,
  useProcureOrder,
  useResumeOrder,
} from '../useOrderActions';

const ORDER_ID = '019cdbf4-e987-7000-8080-000000000001';

function makeWrapper() {
  // gcTime stays > 0 so cache survives the unsubscribed phase of the
  // mutation lifecycle — the optimistic-rollback test reads back the
  // detail key that has no observer attached, which would be GC'd
  // immediately under the default test config.
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

function stub204() {
  vi.stubGlobal(
    'fetch',
    vi.fn(() => Promise.resolve(new Response(null, { status: 204 }))),
  );
}

async function expectInvalidated(client, fn) {
  const spy = vi.spyOn(client, 'invalidateQueries');
  await fn();
  const calledKeys = spy.mock.calls.map(([opts]) => opts?.queryKey);

  // Detail, history, lists() — all three must be touched so any open
  // surface (toolbar / history table / list page) refetches.
  expect(calledKeys).toEqual(
    expect.arrayContaining([
      orderKeys.detail(ORDER_ID),
      orderKeys.history(ORDER_ID),
      orderKeys.lists(),
    ]),
  );
}

describe('useOrderActions — invalidation on success', () => {
  it('useProcureOrder invalidates detail/history/lists', async () => {
    stub204();
    const { client, Wrapper } = makeWrapper();
    const { result } = renderHook(() => useProcureOrder(ORDER_ID), {
      wrapper: Wrapper,
    });
    await expectInvalidated(client, async () => {
      await act(async () => {
        await result.current.mutateAsync({ incomingDeclaration: 'CN-AB-1' });
      });
    });
  });

  it('useHoldOrder invalidates detail/history/lists', async () => {
    stub204();
    const { client, Wrapper } = makeWrapper();
    const { result } = renderHook(() => useHoldOrder(ORDER_ID), {
      wrapper: Wrapper,
    });
    await expectInvalidated(client, async () => {
      await act(async () => {
        await result.current.mutateAsync({ reason: 'manager_review' });
      });
    });
  });

  it('useResumeOrder invalidates detail/history/lists', async () => {
    stub204();
    const { client, Wrapper } = makeWrapper();
    const { result } = renderHook(() => useResumeOrder(ORDER_ID), {
      wrapper: Wrapper,
    });
    await expectInvalidated(client, async () => {
      await act(async () => {
        await result.current.mutateAsync();
      });
    });
  });

  it('useForceCancelOrder invalidates detail/history/lists', async () => {
    stub204();
    const { client, Wrapper } = makeWrapper();
    const { result } = renderHook(() => useForceCancelOrder(ORDER_ID), {
      wrapper: Wrapper,
    });
    await expectInvalidated(client, async () => {
      await act(async () => {
        await result.current.mutateAsync({
          reason: 'customer_changed_mind',
          idempotencyKey: 'idem-key-12345678',
        });
      });
    });
  });

  it('useChangePickupPoint invalidates detail/history/lists', async () => {
    stub204();
    const { client, Wrapper } = makeWrapper();
    const { result } = renderHook(() => useChangePickupPoint(ORDER_ID), {
      wrapper: Wrapper,
    });
    await expectInvalidated(client, async () => {
      await act(async () => {
        await result.current.mutateAsync({
          carrier: 'cdek',
          pointId: 'CDEK-MSK-001',
        });
      });
    });
  });
});

describe('useHoldOrder — optimistic update + rollback', () => {
  it('applies an optimistic hold and rolls back on backend failure', async () => {
    const { client, Wrapper } = makeWrapper();

    // Seed cached detail with a non-hold status so the optimistic flip is observable.
    client.setQueryData(orderKeys.detail(ORDER_ID), {
      orderId: ORDER_ID,
      status: 'paid',
      preHoldStatus: null,
      holdReason: null,
    });

    vi.stubGlobal(
      'fetch',
      vi.fn(() =>
        Promise.resolve(
          new Response(
            JSON.stringify({
              error: {
                code: 'ORDER_INVALID_TRANSITION',
                message: 'bad',
                details: {},
              },
            }),
            { status: 422, headers: { 'Content-Type': 'application/json' } },
          ),
        ),
      ),
    );

    const { result } = renderHook(() => useHoldOrder(ORDER_ID), {
      wrapper: Wrapper,
    });

    await act(async () => {
      await result.current
        .mutateAsync({ reason: 'manager_review' })
        .catch(() => undefined);
    });

    // After rollback the detail must be exactly the pre-mutation snapshot.
    expect(client.getQueryData(orderKeys.detail(ORDER_ID))).toMatchObject({
      status: 'paid',
      preHoldStatus: null,
      holdReason: null,
    });
  });
});
