// TanStack Query key factory — see https://tkdodo.eu/blog/effective-react-query-keys.
//
// `lists()` is the collection key used for invalidation/cache eviction.
// Add a `list(filters)` entry here if/when filtered fetches are introduced.
export const supplierKeys = {
  all: ['suppliers'],
  lists: () => [...supplierKeys.all, 'list'],
};
