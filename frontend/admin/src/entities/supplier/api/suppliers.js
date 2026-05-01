import { apiClient } from '@/shared/api/client-fetch';

export async function fetchSuppliers() {
  const data = await apiClient.get('/api/suppliers');
  const items = (data.items ?? []).filter((s) => s.isActive);
  return { items, total: items.length };
}

export function createSupplier(payload) {
  return apiClient.post('/api/suppliers', payload);
}
