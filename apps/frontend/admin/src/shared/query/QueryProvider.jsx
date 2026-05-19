'use client';

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import dynamic from 'next/dynamic';
import { useState } from 'react';

import {
  DEFAULT_GC_TIME_MS,
  DEFAULT_RETRY_COUNT,
  DEFAULT_STALE_TIME_MS,
} from './defaults';

// Dynamic import is module-level so the loader is hoisted, but the actual
// `<ReactQueryDevtools />` element is only rendered when NODE_ENV === 'development'.
// In a production build, `process.env.NODE_ENV === 'development'` folds to
// `false` at compile time, so the JSX branch and its dynamic chunk are dropped
// from the bundle entirely.
const ReactQueryDevtools = dynamic(
  () =>
    import('@tanstack/react-query-devtools').then(
      (mod) => mod.ReactQueryDevtools,
    ),
  { ssr: false, loading: () => null },
);

/**
 * Single QueryClient instance per render tree (per browser tab).
 * Lifted into useState so it survives StrictMode double-render in dev.
 *
 * Defaults tuned for an admin tool:
 *   - 30s staleTime: most lists are fine to cache for half a minute.
 *   - No refetchOnWindowFocus: admin users tab-switch constantly between
 *     dashboards and the catalogue, focus refetch creates noise.
 *   - Retry up to 2x for transient (5xx, network) failures, but never for
 *     4xx — those are user-actionable errors and should surface immediately.
 *     429 (RATE_LIMITED) falls through this 4xx branch with no auto-retry;
 *     callers should display `error.retryAfter` and let the user retry.
 *   - Mutations don't auto-retry; the caller decides via useMutation options.
 */
function makeQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: DEFAULT_STALE_TIME_MS,
        gcTime: DEFAULT_GC_TIME_MS,
        refetchOnWindowFocus: false,
        retry: (failureCount, error) => {
          const status = error?.status;
          if (typeof status === 'number' && status >= 400 && status < 500) {
            return false;
          }
          return failureCount < DEFAULT_RETRY_COUNT;
        },
      },
      mutations: {
        retry: false,
      },
    },
  });
}

const isDevelopment = process.env.NODE_ENV === 'development';

export function QueryProvider({ children }) {
  const [client] = useState(() => makeQueryClient());

  return (
    <QueryClientProvider client={client}>
      {children}
      {isDevelopment && (
        <ReactQueryDevtools
          initialIsOpen={false}
          buttonPosition="bottom-left"
        />
      )}
    </QueryClientProvider>
  );
}
