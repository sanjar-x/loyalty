import { apiClient } from '@/shared/api/client-fetch';

const DEFAULT_LIMIT = 20;
const DEFAULT_SORT_BY = 'created_at';
const DEFAULT_SORT_ORDER = 'desc';

function buildIdentitiesQuery({
  page = 1,
  limit = DEFAULT_LIMIT,
  search,
  roleId,
  isActive,
  sortBy = DEFAULT_SORT_BY,
  sortOrder = DEFAULT_SORT_ORDER,
} = {}) {
  const params = new URLSearchParams();
  params.set('offset', String((page - 1) * limit));
  params.set('limit', String(limit));
  params.set('sortBy', sortBy);
  params.set('sortOrder', sortOrder);
  if (search?.trim()) params.set('search', search.trim());
  if (roleId) params.set('roleId', roleId);
  if (isActive !== undefined && isActive !== '')
    params.set('isActive', String(isActive));
  return params.toString();
}

export async function fetchIdentities(filters = {}) {
  const data = await apiClient.get(
    `/api/admin/identities?${buildIdentitiesQuery(filters)}`,
  );
  // Endpoint returns either an array or { items, total }; normalise both.
  if (Array.isArray(data)) {
    return { items: data, total: data.length };
  }
  return {
    items: data.items ?? [],
    total:
      typeof data.total === 'number' ? data.total : (data.items?.length ?? 0),
  };
}

export const fetchIdentity = (identityId) =>
  apiClient.get(`/api/admin/identities/${identityId}`);

export const assignIdentityRole = (identityId, roleId) =>
  apiClient.post(`/api/admin/identities/${identityId}/roles`, { roleId });

export const revokeIdentityRole = (identityId, roleId) =>
  apiClient.del(`/api/admin/identities/${identityId}/roles/${roleId}`);

export const deactivateIdentity = (identityId, reason = 'admin_action') =>
  apiClient.post(`/api/admin/identities/${identityId}/deactivate`, { reason });

export const reactivateIdentity = (identityId) =>
  apiClient.post(`/api/admin/identities/${identityId}/reactivate`);
