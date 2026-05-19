// TanStack Query key factories — see https://tkdodo.eu/blog/effective-react-query-keys.
export const customerKeys = {
  all: ['customers'],
  lists: () => [...customerKeys.all, 'list'],
  list: (filters) => [...customerKeys.lists(), filters],
  details: () => [...customerKeys.all, 'detail'],
  detail: (identityId) => [...customerKeys.details(), identityId],
};
