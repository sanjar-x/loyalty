'use client';

import {
  keepPreviousData,
  useInfiniteQuery,
  useQuery,
} from '@tanstack/react-query';

import {
  fetchCancellationReasonsMeta,
  getOrderById,
  getOrderHistory,
  getOrderTracking,
  listOrders,
} from './orders';
import { orderKeys } from './keys';

const META_STALE_TIME_MS = 30 * 60 * 1000;

/**
 * Cursor-paginated orders list.
 *
 * Backend returns `{ items, nextCursor }`; we rely on `useInfiniteQuery` so
 * the consumer can grow the list page-by-page via `fetchNextPage`. The page
 * key intentionally excludes the cursor itself — TanStack assembles pages on
 * top of the same logical key, and `placeholderData: keepPreviousData` keeps
 * the previous batch visible while a new filter combo loads.
 */
export function useOrders({ statuses, limit = 50 } = {}) {
  return useInfiniteQuery({
    queryKey: orderKeys.list({ statuses, limit }),
    queryFn: ({ pageParam }) =>
      listOrders({ statuses, limit, cursor: pageParam ?? undefined }),
    initialPageParam: undefined,
    getNextPageParam: (lastPage) => lastPage?.nextCursor ?? undefined,
    placeholderData: keepPreviousData,
  });
}

export function useOrder(orderId) {
  return useQuery({
    queryKey: orderKeys.detail(orderId),
    queryFn: () => getOrderById(orderId),
    enabled: Boolean(orderId),
  });
}

export function useOrderHistory(orderId) {
  return useQuery({
    queryKey: orderKeys.history(orderId),
    queryFn: () => getOrderHistory(orderId),
    enabled: Boolean(orderId),
  });
}

export function useOrderTracking(orderId) {
  return useQuery({
    queryKey: orderKeys.tracking(orderId),
    queryFn: () => getOrderTracking(orderId),
    enabled: Boolean(orderId),
  });
}

/**
 * Cached cancellation-reason taxonomy (backend path:
 * `/api/v1/admin/orders/_meta/cancellation-reasons`; BFF surface:
 * `/api/admin/orders/meta/cancellation-reasons` — the underscore is
 * dropped on the front because Next.js opts `_*` folders out of
 * routing).
 *
 * The taxonomy is effectively static (a backend release would bump it),
 * so the 30-minute staleTime keeps the modal open instantly on every
 * subsequent render. The cache is keyed by
 * `orderKeys.meta('cancellation-reasons')` — an admin who never opens
 * ForceCancelModal never pays for the fetch.
 */
export function useCancellationReasons() {
  return useQuery({
    queryKey: orderKeys.meta('cancellation-reasons'),
    queryFn: fetchCancellationReasonsMeta,
    staleTime: META_STALE_TIME_MS,
  });
}
