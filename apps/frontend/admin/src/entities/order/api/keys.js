// TanStack Query key factory — see https://tkdodo.eu/blog/effective-react-query-keys.
//
// Filters object is part of the list key (cursor-based pagination uses the
// statuses + limit subset; the cursor itself is NOT in the key — InfiniteQuery
// composes pages on top of the same logical key).
export const orderKeys = {
  all: ['orders'],
  lists: () => [...orderKeys.all, 'list'],
  list: (filters) => [...orderKeys.lists(), filters],
  details: () => [...orderKeys.all, 'detail'],
  detail: (orderId) => [...orderKeys.details(), orderId],
  history: (orderId) => [...orderKeys.detail(orderId), 'history'],
  tracking: (orderId) => [...orderKeys.detail(orderId), 'tracking'],
  // Static taxonomy fetched once per session (`cancellation-reasons` etc.).
  // Slug is the `_meta/<slug>` path tail — keeps the key flat while leaving
  // room for additional taxonomies (eg. hold-reasons) without re-shuffling
  // the existing keys.
  meta: (slug) => [...orderKeys.all, 'meta', slug],
};
