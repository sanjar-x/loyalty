// TanStack Query key factories — see https://tkdodo.eu/blog/effective-react-query-keys.
export const customerKeys = {
  all: ['customers'],
  lists: () => [...customerKeys.all, 'list'],
  list: (filters) => [...customerKeys.lists(), filters],
  details: () => [...customerKeys.all, 'detail'],
  detail: (identityId) => [...customerKeys.details(), identityId],
};

// `identityKeys` is kept for back-compat with consumers that still hit
// `/admin/identities` (e.g. the staff slice). Customer-only screens should
// use `customerKeys` exclusively so the cache namespaces don't collide.
export const identityKeys = {
  all: ['identities'],
  lists: () => [...identityKeys.all, 'list'],
  list: (filters) => [...identityKeys.lists(), filters],
  details: () => [...identityKeys.all, 'detail'],
  detail: (identityId) => [...identityKeys.details(), identityId],
};
