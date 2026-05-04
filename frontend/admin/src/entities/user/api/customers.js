import { apiClient } from '@/shared/api/client-fetch';

// `/admin/customers` is a customer-only projection of identities; it does NOT
// support `role_id` filtering (every customer carries the `customer` role).
const DEFAULT_LIMIT = 20;
const DEFAULT_SORT = 'created_at:desc';

// Maps the dropdown value to the backend `sort_by` + `sort_order` pair.
// Whitelist matches the OpenAPI regex `^(created_at|email|last_name)$`.
export const CUSTOMER_SORT_OPTIONS = [
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

function buildCustomersQuery({
  page = 1,
  limit = DEFAULT_LIMIT,
  search,
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
  if (isActive !== undefined && isActive !== '' && isActive !== null) {
    params.set('is_active', String(isActive));
  }
  return params.toString();
}

export async function fetchCustomers(filters = {}) {
  const data = await apiClient.get(
    `/api/admin/customers?${buildCustomersQuery(filters)}`,
  );
  return {
    items: Array.isArray(data?.items) ? data.items : [],
    total: typeof data?.total === 'number' ? data.total : 0,
    offset: typeof data?.offset === 'number' ? data.offset : 0,
    limit: typeof data?.limit === 'number' ? data.limit : DEFAULT_LIMIT,
  };
}

export const fetchCustomer = (identityId) =>
  apiClient.get(`/api/admin/customers/${identityId}`);

export const deactivateCustomer = (identityId, reason) =>
  apiClient.post(`/api/admin/customers/${identityId}/deactivate`, { reason });

export const reactivateCustomer = (identityId) =>
  apiClient.post(`/api/admin/customers/${identityId}/reactivate`);
