/**
 * RTKQ endpoint enhancement config'lari — Favorites (lists + items + bulk).
 */
export const favoriteEndpoints = {
  /* ─── Favorites ─── */
  // Lists: response `{items: FavoriteListResponse[]}` — flat array'ga unwrap.
  // Tag granularity: "LISTS" rosteri + har list uchun id-tag (rename/delete'da
  // shu listga tegishli items cache'i ham invalidate bo'lsin).
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
  // Items: cursor-pagination saqlangan holda `items` array'ini ko'taramiz.
  // Cache key arg.{listId, targetType, cursor, limit} — har target_type
  // uchun alohida cache (product/brand sahifa orasida konflikt bo'lmaydi).
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
  // Add/remove/move: granular invalidatsiya o'rniga keng `Favorites` —
  // bulk-check cache, lists, items hammasini bir zumda yangilashga olib
  // keladi. `useItemFavorites` optimistic patch beradi, shuning uchun
  // refetch ham latency hissi bermaydi.
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
