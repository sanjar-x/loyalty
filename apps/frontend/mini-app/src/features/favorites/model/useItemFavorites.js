'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useDispatch } from 'react-redux';

import { api } from '@/app/providers/store/instance';
import {
  useAddFavoriteItemMutation,
  useListFavoriteItemsQuery,
  useRemoveFavoriteItemMutation,
} from '@/entities/favorite';
import { useFavoriteLists } from '@/features/favorites/model/useFavoriteLists';
import { humanizeApiError } from '@/shared/api/errors';
import { toast } from '@/shared/ui/Toaster';

/** Telegram WebApp tactile feedback — gives a physical signal on button press.
 *  Without waiting for the network response, the user feels "the button worked".
 *  In an environment without a Telegram client this is a no-op (browser dev). */
function tactileBounce() {
  if (typeof window === 'undefined') return;
  try {
    window.Telegram?.WebApp?.HapticFeedback?.impactOccurred?.('light');
  } catch {
    // ignore — non-Telegram host
  }
}

/**
 * Hook implementing the v1 favorites contract.
 *
 * Domain mapping:
 *  • `targetType` ∈ ["product", "brand"] — backend `FavoriteTargetType` enum.
 *  • `targetId` — UUID string (catalog Product.id / Brand.id).
 *  • The backend auto-provides a single default `FavoriteList` per caller.
 *    If `list_id` is omitted in the add request, the server attaches it to
 *    its own default list — we don't implement frontend lazy-create logic here.
 *
 * Returns API (compatible with the legacy contract):
 *  • `favoriteItemIds: Set<string>` — set of favorited target_ids.
 *    Pages drive the heart icon via `favoriteItemIds.has(target.id)`.
 *    The optimistic toggle effect is reflected in this Set immediately.
 *  • `favorites: FavoriteItemResponse[]` — raw items inside the list
 *    (with enriched `product`/`brand` card).
 *  • `targetIdToFavoriteItem: Map<string, FavoriteItemResponse>` —
 *    target_id → item map. Pages can render via the enriched card from
 *    the stored data.
 *  • `toggleFavorite(targetId)` — accepts a UUID. Unaccounted in-flight
 *    calls are throttled (per-targetId ref-Set).
 *
 * Optimistic strategy:
 *  • On toggle press, `targetId → desired` is written into the
 *    `optimisticMap` Set immediately. The UI sees the effective Set from
 *    here (doesn't wait for the server response).
 *  • The mutation result invalidates the `Favorites` tags → list items
 *    and bulk-check caches refetch → the optimistic patch is removed.
 *  • If the mutation fails, the optimistic patch is rolled back (UI
 *    returns to the previous state). We don't throw — the isError flag is
 *    exposed so the UI can show a toast.
 *
 * Limitation: currently a single `useListFavoriteItemsQuery` fetches the
 * **first page** filtered by `target_type` inside the default list
 * (limit: 100). For 100+ favorites we'd need to add cursor pagination.
 */
export function useItemFavorites(targetType) {
  const type = targetType === 'brand' ? 'brand' : 'product';
  const dispatch = useDispatch();

  const { defaultListId, isAuthenticated, isLoading: isListsLoading } = useFavoriteLists();

  const skipItemsQuery = !isAuthenticated || !defaultListId;

  const {
    data: itemsPage,
    isLoading: isItemsLoading,
    isFetching: isItemsFetching,
    isError,
    refetch,
  } = useListFavoriteItemsQuery(
    {
      listId: defaultListId,
      targetType: type,
      limit: 100,
    },
    { skip: skipItemsQuery }
  );

  const favorites = useMemo(
    () => (Array.isArray(itemsPage?.items) ? itemsPage.items : []),
    [itemsPage]
  );

  // target_id (UUID) → enriched FavoriteItemResponse. Pages get the full
  // item from this map for the product card image/name.
  const targetIdToFavoriteItem = useMemo(() => {
    const m = new Map();
    for (const it of favorites) {
      if (!it || typeof it !== 'object') continue;
      const tid = it.target_id;
      if (typeof tid !== 'string' || !tid) continue;
      m.set(tid, it);
    }
    return m;
  }, [favorites]);

  // target_id → list_id. The remove mutation requires 3 path params —
  // we find listId via this map (an item might be in a different list;
  // even though we're only reading the default, this is a robust handle).
  const targetIdToListId = useMemo(() => {
    const m = new Map();
    for (const it of favorites) {
      if (!it || typeof it !== 'object') continue;
      const tid = it.target_id;
      const lid = it.list_id;
      if (typeof tid !== 'string' || typeof lid !== 'string') continue;
      m.set(tid, lid);
    }
    return m;
  }, [favorites]);

  const serverFavoriteIds = useMemo(
    () => new Set(targetIdToFavoriteItem.keys()),
    [targetIdToFavoriteItem]
  );

  // Optimistic patch: target_id → boolean (desired state).
  const [optimisticMap, setOptimisticMap] = useState(() => new Map());
  const inflightRef = useRef(new Set());

  const favoriteItemIds = useMemo(() => {
    if (!optimisticMap.size) return serverFavoriteIds;
    const out = new Set(serverFavoriteIds);
    for (const [tid, desired] of optimisticMap.entries()) {
      if (desired) out.add(tid);
      else out.delete(tid);
    }
    return out;
  }, [serverFavoriteIds, optimisticMap]);

  // Reconciliation: drop the optimistic patch by matching against the
  // server-side value. After a successful mutation the RTKQ refetch may
  // not have finished — if we drop optimistic now, the UI flicks back to
  // the old state for a moment. Instead: keep the optimistic patch and
  // drop it automatically when the server returns the new value (refetch
  // completed and `serverFavoriteIds` equals the desired value) — the UI
  // never reverses.
  useEffect(() => {
    if (optimisticMap.size === 0) return;
    setOptimisticMap((prev) => {
      let changed = false;
      const next = new Map(prev);
      for (const [tid, desired] of prev) {
        const serverHas = serverFavoriteIds.has(tid);
        if (serverHas === desired) {
          next.delete(tid);
          changed = true;
        }
      }
      return changed ? next : prev;
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [serverFavoriteIds]);

  const [addFavoriteItem, addState] = useAddFavoriteItemMutation();
  const [removeFavoriteItem, removeState] = useRemoveFavoriteItemMutation();

  const isMutating = Boolean(addState.isLoading || removeState.isLoading);

  const toggleFavorite = useCallback(
    async (rawTargetId) => {
      if (!isAuthenticated) {
        // User isn't signed in — not a silent fail, warn with a toast
        // (the project uses Telegram-only auth, this path is common in
        // dev preview).
        toast.error('Войдите в аккаунт, чтобы добавлять в избранное');
        return;
      }

      const targetId =
        typeof rawTargetId === 'string'
          ? rawTargetId
          : rawTargetId == null
            ? ''
            : String(rawTargetId);
      if (!targetId) return;

      // Concurrent presses on the same target — don't start the second
      // before the first finishes (so the toggle sequence doesn't slip).
      if (inflightRef.current.has(targetId)) return;

      const currentlyFavorite = favoriteItemIds.has(targetId);
      const nextDesired = !currentlyFavorite;

      // 1. Instant UI feedback (sync, before render starts):
      //    – the optimistic Map is updated (UI changes immediately)
      //    – haptic bounce in the Telegram WebApp (physical signal)
      tactileBounce();
      setOptimisticMap((prev) => {
        const next = new Map(prev);
        next.set(targetId, nextDesired);
        return next;
      });
      inflightRef.current.add(targetId);

      try {
        if (nextDesired) {
          // Add: list_id is optional — the server attaches to the default list.
          // If `list_id` is undefined the property isn't added to the object
          // at all → JSON.stringify skips it → the server attaches to its
          // own default list (lazy-create). We don't send empty string / null
          // — that's an unnecessary cause of error for the backend pattern.
          const body = {
            target_type: type,
            target_id: targetId,
          };
          if (defaultListId) body.list_id = defaultListId;

          try {
            await addFavoriteItem({ addFavoriteItemRequest: body }).unwrap();
          } catch (err) {
            // Rollback optimistic — server doesn't have it, UI to `false` too.
            setOptimisticMap((prev) => {
              const next = new Map(prev);
              next.set(targetId, false);
              return next;
            });
            toast.error(humanizeApiError(err, 'Не удалось добавить в избранное'));
          }
        } else {
          const listId = targetIdToListId.get(targetId) ?? defaultListId;
          if (!listId) {
            // No list ID found — server hasn't created the default list yet.
            // Cancel the optimistic patch and exit.
            setOptimisticMap((prev) => {
              if (!prev.has(targetId)) return prev;
              const next = new Map(prev);
              next.delete(targetId);
              return next;
            });
            return;
          }
          try {
            await removeFavoriteItem({
              listId,
              targetType: type,
              targetId,
            }).unwrap();
          } catch (err) {
            setOptimisticMap((prev) => {
              const next = new Map(prev);
              next.set(targetId, true);
              return next;
            });
            toast.error(humanizeApiError(err, 'Не удалось убрать из избранного'));
          }
        }

        // PDP cache invalidation — if `is_favorite` were a denormalized field
        // the new value would come from the server (not in the current
        // backend, but kept as a safety net for the future). We don't drop
        // the optimistic patch here — the useEffect reconciliation clears it
        // on its own when the server updates `serverFavoriteIds` (the single
        // place that prevents UI flicker).
        if (type === 'product') {
          dispatch(api.util.invalidateTags([{ type: 'Product', id: targetId }]));
        }
      } finally {
        inflightRef.current.delete(targetId);
      }
    },
    [
      addFavoriteItem,
      defaultListId,
      dispatch,
      favoriteItemIds,
      isAuthenticated,
      removeFavoriteItem,
      targetIdToListId,
      type,
    ]
  );

  return {
    favorites,
    favoriteItemIds,
    targetIdToFavoriteItem,
    targetIdToListId,
    toggleFavorite,
    isLoading: Boolean(isListsLoading || isItemsLoading),
    isFetching: Boolean(isItemsFetching),
    isError,
    isMutating,
    refetch,
  };
}
