// TanStack Query key factory — see https://tkdodo.eu/blog/effective-react-query-keys.
export const productKeys = {
  all: ['products'],
  lists: () => [...productKeys.all, 'list'],
  list: (filters) => [...productKeys.lists(), filters],
  details: () => [...productKeys.all, 'detail'],
  detail: (productId) => [...productKeys.details(), productId],
  completeness: (productId) => [
    ...productKeys.detail(productId),
    'completeness',
  ],
  media: (productId) => [...productKeys.detail(productId), 'media'],
  // Publish-gate verdict & diagnostics — refetched on every focus + on
  // SSE pricing events so the UI matches the live recompute pipeline.
  validatePublish: (productId) => [
    ...productKeys.detail(productId),
    'validate-publish',
  ],
  // Update preview is keyed by the payload digest so two concurrent
  // edits (e.g. two browser tabs) don't share a cached verdict.
  validateUpdate: (productId, digest) => [
    ...productKeys.detail(productId),
    'validate-update',
    digest,
  ],
};
