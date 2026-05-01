// TanStack Query key factory — see https://tkdodo.eu/blog/effective-react-query-keys.
export const productKeys = {
  all: ['products'],
  lists: () => [...productKeys.all, 'list'],
  list: (filters) => [...productKeys.lists(), filters],
  counts: () => [...productKeys.all, 'counts'],
  details: () => [...productKeys.all, 'detail'],
  detail: (productId) => [...productKeys.details(), productId],
  completeness: (productId) => [
    ...productKeys.detail(productId),
    'completeness',
  ],
  media: (productId) => [...productKeys.detail(productId), 'media'],
};
