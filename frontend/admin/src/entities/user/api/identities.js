import { apiClient } from '@/shared/api/client-fetch';

// `/admin/identities` query parameters are snake_case on the backend
// (FastAPI Pydantic), so the frontend must serialise filters with snake keys
// — sending `roleId`/`isActive`/`sortBy` would silently bypass filtering.
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
  params.set('offset', String(Math.max(0, (page - 1) * limit)));
  params.set('limit', String(limit));
  params.set('sort_by', sortBy);
  params.set('sort_order', sortOrder);
  if (search?.trim()) params.set('search', search.trim());
  if (roleId) params.set('role_id', roleId);
  if (isActive !== undefined && isActive !== '' && isActive !== null) {
    params.set('is_active', String(isActive));
  }
  return params.toString();
}

export async function fetchIdentities(filters = {}) {
  const data = await apiClient.get(
    `/api/admin/identities?${buildIdentitiesQuery(filters)}`,
  );
  return {
    items: Array.isArray(data?.items) ? data.items : [],
    total: typeof data?.total === 'number' ? data.total : 0,
    offset: typeof data?.offset === 'number' ? data.offset : 0,
    limit: typeof data?.limit === 'number' ? data.limit : DEFAULT_LIMIT,
  };
}

export const fetchIdentity = (identityId) =>
  apiClient.get(`/api/admin/identities/${identityId}`);

export const assignIdentityRole = (identityId, roleId) =>
  apiClient.post(`/api/admin/identities/${identityId}/roles`, { roleId });

export const revokeIdentityRole = (identityId, roleId) =>
  apiClient.del(`/api/admin/identities/${identityId}/roles/${roleId}`);

export const deactivateIdentity = (identityId, reason) =>
  apiClient.post(`/api/admin/identities/${identityId}/deactivate`, { reason });

export const reactivateIdentity = (identityId) =>
  apiClient.post(`/api/admin/identities/${identityId}/reactivate`);
