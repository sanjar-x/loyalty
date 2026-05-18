'use client';

import { useMemo } from 'react';

import { useGetFavoriteListsQuery, useCreateFavoriteListMutation } from '@/entities/favorite';
import { useAuthStore, AuthStatus } from '@/entities/user';

/**
 * Single entry point for working with the user's favorite collections
 * (FavoriteList). The backend is expected to auto-provide a default list
 * with `is_default: true` for every authenticated caller (server
 * lazy-create). If it isn't there — the frontend creates a new list named
 * "Избранное" and returns its ID (best-effort, on the second visit it
 * comes from the cache).
 *
 * Auth gate: if the caller isn't `AUTHENTICATED` — the query is skipped
 * and the hook returns empty data. Other hooks (useItemFavorites) rely on
 * this signal to conditionally enable bulk-check and items queries.
 */
export function useFavoriteLists() {
  const isAuthenticated = useAuthStore((s) => s.status === AuthStatus.AUTHENTICATED);

  const {
    data: lists,
    isLoading,
    isFetching,
    isError,
    refetch,
  } = useGetFavoriteListsQuery(undefined, { skip: !isAuthenticated });

  const items = useMemo(() => (Array.isArray(lists) ? lists : []), [lists]);

  const defaultList = useMemo(() => {
    if (!items.length) return null;
    return items.find((l) => l && l.is_default === true) ?? items[0] ?? null;
  }, [items]);

  return {
    lists: items,
    defaultList,
    defaultListId: defaultList?.id ?? null,
    isAuthenticated,
    isLoading,
    isFetching,
    isError,
    refetch,
  };
}

/**
 * Convenience: for callers that only want the default list ID
 * (the toggle handler adds to the default list). `null` when not authed.
 */
export function useDefaultFavoriteListId() {
  return useFavoriteLists().defaultListId;
}

/**
 * Imperative "ensure default list exists" — if the backend hasn't
 * lazy-created it, opens a new list named "Избранное" and returns its ID.
 * Concurrent calls see the refetch and don't step on each other (a
 * server-side unique constraint is required).
 */
export function useEnsureDefaultList() {
  const { defaultListId, lists, refetch } = useFavoriteLists();
  const [createList] = useCreateFavoriteListMutation();

  return async function ensure() {
    if (defaultListId) return defaultListId;
    if (Array.isArray(lists) && lists.length > 0) {
      return lists[0]?.id ?? null;
    }
    try {
      const created = await createList({
        createFavoriteListRequest: { name: 'Избранное' },
      }).unwrap();
      const id = created?.id ?? null;
      // Short refetch until the is_default flag is visible in cache.
      try {
        await refetch?.()?.catch?.(() => null);
      } catch {
        // ignore
      }
      return id;
    } catch {
      return null;
    }
  };
}
