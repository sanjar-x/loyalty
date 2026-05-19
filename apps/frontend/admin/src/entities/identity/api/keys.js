// TanStack Query key factories — see https://tkdodo.eu/blog/effective-react-query-keys.
//
// Identity scope = the broader IAM record covering staff + customers.
// Customer-only screens should use `entities/customer/customerKeys`
// instead so the cache namespaces don't collide.
export const identityKeys = {
  all: ['identities'],
  lists: () => [...identityKeys.all, 'list'],
  list: (filters) => [...identityKeys.lists(), filters],
  details: () => [...identityKeys.all, 'detail'],
  detail: (identityId) => [...identityKeys.details(), identityId],
};
