'use client';

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

function makeTestClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0, staleTime: 0 },
      mutations: { retry: false },
    },
  });
}

/**
 * Build a QueryClient + wrapper for renderHook / render in tests.
 *
 * Pass an existing client to share cache between multiple `renderHook` calls
 * (useful for testing invalidation flows). Otherwise each call gets a fresh,
 * fully-isolated client.
 *
 * Usage:
 *   const { Wrapper, client } = createWrapper();
 *   const { result } = renderHook(() => useBrands(), { wrapper: Wrapper });
 *
 *   // shared cache across hooks:
 *   const { Wrapper, client } = createWrapper();
 *   renderHook(() => useBrands(), { wrapper: Wrapper });
 *   renderHook(() => useBrands(), { wrapper: Wrapper });
 *   client.invalidateQueries({ queryKey: ['brands'] });
 */
export function createWrapper(existingClient) {
  const client = existingClient ?? makeTestClient();

  function Wrapper({ children }) {
    return (
      <QueryClientProvider client={client}>{children}</QueryClientProvider>
    );
  }

  return { Wrapper, client };
}
