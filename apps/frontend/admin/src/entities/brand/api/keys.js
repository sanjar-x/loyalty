// TanStack Query key factory — see https://tkdodo.eu/blog/effective-react-query-keys.
export const brandKeys = {
  all: ['brands'],
  lists: () => [...brandKeys.all, 'list'],
  list: (filters) => [...brandKeys.lists(), filters],
  details: () => [...brandKeys.all, 'detail'],
  detail: (brandId) => [...brandKeys.details(), brandId],
};
