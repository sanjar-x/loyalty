'use client';

import { useCallback, useDeferredValue, useMemo, useState } from 'react';

import { ORDER_STATUS_FILTER_GROUPS, useOrders } from '@/entities/order';

const DEFAULT_GROUP_KEY = 'all';
const DEFAULT_LIMIT = 50;

function findGroup(key) {
  return (
    ORDER_STATUS_FILTER_GROUPS.find((g) => g.key === key) ??
    ORDER_STATUS_FILTER_GROUPS[0]
  );
}

/**
 * Filter + pagination state for the orders list.
 *
 * Server-side: `statuses` is the only filter the backend honours today, so
 * the group-key dropdown maps onto the `statuses` query param. Pagination
 * is cursor-based (`useOrders` is an infinite query) — we expose
 * `fetchNextPage` / `hasNextPage` so the page can wire a "Load more" button.
 *
 * Client-side: free-text `search` filters the already-fetched pages by
 * `orderNumber` (raw match). Customer-name search isn't possible until the
 * BE list endpoint enriches the row with the identity name.
 */
export function useOrderFilters({ limit = DEFAULT_LIMIT } = {}) {
  const [groupKey, setGroupKey] = useState(DEFAULT_GROUP_KEY);
  const [search, setSearch] = useState('');
  const deferredSearch = useDeferredValue(search);

  const activeGroup = findGroup(groupKey);
  const statuses = activeGroup.statuses;

  const queryFilters = useMemo(
    () => ({ statuses: statuses ?? undefined, limit }),
    [statuses, limit],
  );

  const {
    data,
    isPending,
    isFetching,
    isError,
    error,
    refetch,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
  } = useOrders(queryFilters);

  const allItems = useMemo(() => {
    const pages = data?.pages ?? [];
    const out = [];
    for (const page of pages) {
      if (Array.isArray(page?.items)) out.push(...page.items);
    }
    return out;
  }, [data]);

  const filteredItems = useMemo(() => {
    const q = deferredSearch.trim().toLowerCase();
    if (!q) return allItems;
    return allItems.filter((order) => {
      if (order.orderNumber?.toLowerCase().includes(q)) return true;
      // identityId is uuid — last 8 chars are the human-recognisable suffix
      if (order.identityId?.toLowerCase().includes(q)) return true;
      return false;
    });
  }, [allItems, deferredSearch]);

  const hasActiveFilters =
    groupKey !== DEFAULT_GROUP_KEY || search.trim() !== '';

  const reset = useCallback(() => {
    setGroupKey(DEFAULT_GROUP_KEY);
    setSearch('');
  }, []);

  return {
    // Filter state
    groupKey,
    setGroupKey,
    search,
    setSearch,
    activeGroup,
    hasActiveFilters,
    reset,

    // Server data
    items: filteredItems,
    rawItems: allItems,
    loading: isPending,
    fetching: isFetching,
    error: isError ? error : null,
    refetch,

    // Cursor pagination
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
  };
}
