/**
 * RTKQ endpoint enhancement configs — Favorites (lists + items + bulk).
 */
export const favoriteEndpoints = {
  /* ─── Favorites ─── */
  // Lists: response `{items: FavoriteListResponse[]}` — unwrapped into a flat array.
  // Tag granularity: a "LISTS" roster plus an id-tag per list (on rename/delete
  // the items cache for that list is also invalidated).
  listFavoriteListsApiV1FavoritesListsGet: {
    transformResponse: (resp) => (Array.isArray(resp?.items) ? resp.items : []),
    providesTags: (lists) => {
      const arr = Array.isArray(lists) ? lists : [];
      return [
        { type: 'Favorites', id: 'LISTS' },
        ...arr
          .map((l) => (l && typeof l === 'object' ? l.id : null))
          .filter((id) => id != null)
          .map((id) => ({ type: 'Favorites', id: `list-${id}` })),
      ];
    },
  },
  // Items: we lift the `items` array while keeping cursor pagination.
  // Cache key arg.{listId, targetType, cursor, limit} — a separate cache per
  // target_type (no conflict between product/brand pages).
  listFavoriteItemsApiV1FavoritesListsListIdItemsGet: {
    transformResponse: (resp) => ({
      items: Array.isArray(resp?.items) ? resp.items : [],
      nextCursor: resp?.next_cursor ?? null,
    }),
    providesTags: (result, _e, arg) => {
      const items = Array.isArray(result?.items) ? result.items : [];
      const scope = `list-${arg?.listId}-items-${arg?.targetType ?? 'all'}`;
      return [
        { type: 'Favorites', id: scope },
        ...items
          .map((it) => (it && typeof it === 'object' ? it.id : null))
          .filter((id) => id != null)
          .map((id) => ({ type: 'Favorites', id: `item-${id}` })),
      ];
    },
    keepUnusedDataFor: 60,
  },
  createFavoriteListApiV1FavoritesListsPost: {
    invalidatesTags: [{ type: 'Favorites', id: 'LISTS' }],
  },
  renameFavoriteListApiV1FavoritesListsListIdPatch: {
    invalidatesTags: (_r, _e, arg) => [
      { type: 'Favorites', id: 'LISTS' },
      { type: 'Favorites', id: `list-${arg?.listId}` },
    ],
  },
  deleteFavoriteListApiV1FavoritesListsListIdDelete: {
    invalidatesTags: (_r, _e, arg) => [
      { type: 'Favorites', id: 'LISTS' },
      { type: 'Favorites', id: `list-${arg?.listId}` },
    ],
  },
  // Add/remove/move: instead of granular invalidation we use the broad
  // `Favorites` — this refreshes the bulk-check cache, lists, and items at
  // once. `useItemFavorites` issues an optimistic patch, so the refetch
  // does not produce a latency feeling either.
  addFavoriteItemApiV1FavoritesItemsPost: {
    invalidatesTags: ['Favorites'],
  },
  removeFavoriteItemApiV1FavoritesListsListIdItemsTargetTypeTargetIdDelete: {
    invalidatesTags: ['Favorites'],
  },
  moveFavoriteItemApiV1FavoritesItemsMovePost: {
    invalidatesTags: ['Favorites'],
  },
};
