// TanStack Query key factory for the attribute slice. Mirrors the
// shape used by other entity slices (brand / order / product) so the
// invalidation conventions stay uniform.
export const attributeKeys = {
  all: ['attributes'],
  lists: () => [...attributeKeys.all, 'list'],
  list: (filters) => [...attributeKeys.lists(), filters],
  details: () => [...attributeKeys.all, 'detail'],
  detail: (attributeId) => [...attributeKeys.details(), attributeId],
  usage: (attributeId) => [...attributeKeys.detail(attributeId), 'usage'],
};
