// TanStack Query key factory — see https://tkdodo.eu/blog/effective-react-query-keys.
export const roleKeys = {
  all: ['roles'],
  lists: () => [...roleKeys.all, 'list'],
  list: (filters) => [...roleKeys.lists(), filters],
  details: () => [...roleKeys.all, 'detail'],
  detail: (roleId) => [...roleKeys.details(), roleId],
};

export const permissionKeys = {
  all: ['permissions'],
  lists: () => [...permissionKeys.all, 'list'],
};
