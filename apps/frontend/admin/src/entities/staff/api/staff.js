import { apiClient } from '@/shared/api/clientFetch';

// Backend `/admin/staff` accepts camelCase query params. Every consumer of
// this module must go through `buildStaffQuery` so filter keys stay correct.
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
  params.set('sortBy', sortBy);
  params.set('sortOrder', sortOrder);
  if (search?.trim()) params.set('search', search.trim());
  if (roleId) params.set('roleId', roleId);
  if (isActive !== undefined && isActive !== '' && isActive !== null) {
    params.set('isActive', String(isActive));
  }
  return params.toString();
}

// Backend exposes two diagnostic flags per row:
//   accountTypeMismatch — identity is CUSTOMER but carries a staff-role.
//   hasStaffMemberProfile — identity exists but no staff_members row.
// Both default to "no anomaly" (false / true) so older snapshots and
// any future field omission read as a clean row.
function normalizeStaffItem(raw) {
  if (!raw || typeof raw !== 'object') return raw;
  return {
    ...raw,
    firstName: raw.firstName ?? null,
    lastName: raw.lastName ?? null,
    accountTypeMismatch: Boolean(raw.accountTypeMismatch),
    hasStaffMemberProfile:
      raw.hasStaffMemberProfile === undefined
        ? true
        : Boolean(raw.hasStaffMemberProfile),
  };
}

export async function fetchStaffList(filters = {}) {
  const data = await apiClient.get(
    `/api/admin/staff?${buildStaffQuery(filters)}`,
  );
  return {
    items: Array.isArray(data?.items) ? data.items.map(normalizeStaffItem) : [],
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
