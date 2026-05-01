// TanStack Query key factory — see https://tkdodo.eu/blog/effective-react-query-keys.
export const identityKeys = {
  all: ['identities'],
  lists: () => [...identityKeys.all, 'list'],
  list: (filters) => [...identityKeys.lists(), filters],
  details: () => [...identityKeys.all, 'detail'],
  detail: (identityId) => [...identityKeys.details(), identityId],
};
