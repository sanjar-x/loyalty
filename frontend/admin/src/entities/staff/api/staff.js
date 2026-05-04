import { apiClient } from '@/shared/api/client-fetch';

// Backend `/admin/staff` accepts snake_case query (FastAPI Pydantic). Sending
// camelCase silently bypasses filtering — every consumer of this module must
// go through `buildStaffQuery`.
const DEFAULT_LIMIT = 20;
const DEFAULT_SORT = 'created_at:desc';

export const STAFF_SORT_OPTIONS = [
  { value: 'created_at:desc', label: 'Сначала новые' },
  { value: 'created_at:asc', label: 'Сначала старые' },
  { value: 'last_name:asc', label: 'По имени А–Я' },
  { value: 'last_name:desc', label: 'По имени Я–А' },
  { value: 'email:asc', label: 'По email А–Я' },
  { value: 'email:desc', label: 'По email Я–А' },
];

function parseSort(value) {
  const [sortBy, sortOrder] = String(value || DEFAULT_SORT).split(':');
  return {
    sortBy: sortBy || 'created_at',
    sortOrder: sortOrder === 'asc' ? 'asc' : 'desc',
  };
}

function buildStaffQuery({
  page = 1,
  limit = DEFAULT_LIMIT,
  search,
  roleId,
  isActive,
  sort,
} = {}) {
  const { sortBy, sortOrder } = parseSort(sort);
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

export async function fetchStaffList(filters = {}) {
  const data = await apiClient.get(
    `/api/admin/staff?${buildStaffQuery(filters)}`,
  );
  return {
    items: Array.isArray(data?.items) ? data.items : [],
    total: typeof data?.total === 'number' ? data.total : 0,
    offset: typeof data?.offset === 'number' ? data.offset : 0,
    limit: typeof data?.limit === 'number' ? data.limit : DEFAULT_LIMIT,
  };
}

export const fetchStaffMember = (identityId) =>
  apiClient.get(`/api/admin/staff/${identityId}`);

export const deactivateStaff = (identityId, reason) =>
  apiClient.post(`/api/admin/staff/${identityId}/deactivate`, { reason });

export const reactivateStaff = (identityId) =>
  apiClient.post(`/api/admin/staff/${identityId}/reactivate`);
