import { renderHook, waitFor } from '@testing-library/react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { describe, expect, it } from 'vitest';
import { act } from 'react';
import { createWrapper } from '../test-utils';

describe('QueryProvider / TanStack Query wiring', () => {
  it('returns success status with resolved data', async () => {
    const { Wrapper } = createWrapper();
    const { result } = renderHook(
      () =>
        useQuery({
          queryKey: ['smoke', 'success'],
          queryFn: () => Promise.resolve({ ok: true }),
        }),
      { wrapper: Wrapper },
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual({ ok: true });
  });

  it('exposes thrown errors as `error`', async () => {
    const { Wrapper } = createWrapper();
    const { result } = renderHook(
      () =>
        useQuery({
          queryKey: ['smoke', 'error'],
          queryFn: () => Promise.reject(new Error('boom')),
          retry: false,
        }),
      { wrapper: Wrapper },
    );

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.error?.message).toBe('boom');
  });

  it('useMutation runs and surfaces success', async () => {
    const { Wrapper } = createWrapper();
    const { result } = renderHook(
      () => useMutation({ mutationFn: (n) => Promise.resolve(n * 2) }),
      { wrapper: Wrapper },
    );

    const data = await act(() => result.current.mutateAsync(21));
    expect(data).toBe(42);
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
  });

  it('exposes the QueryClient for cache assertions', async () => {
    const { Wrapper, client } = createWrapper();
    const { result } = renderHook(
      () =>
        useQuery({
          queryKey: ['smoke', 'cache'],
          queryFn: () => Promise.resolve('cached'),
        }),
      { wrapper: Wrapper },
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(client.getQueryData(['smoke', 'cache'])).toBe('cached');
  });
});
