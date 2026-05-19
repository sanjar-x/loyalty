// TanStack Query key factory — see https://tkdodo.eu/blog/effective-react-query-keys.
export const providerAccountKeys = {
  all: ['logistics-providers'],
  lists: () => [...providerAccountKeys.all, 'list'],
  list: (filters) => [...providerAccountKeys.lists(), filters],
  details: () => [...providerAccountKeys.all, 'detail'],
  detail: (id) => [...providerAccountKeys.details(), id],
};
