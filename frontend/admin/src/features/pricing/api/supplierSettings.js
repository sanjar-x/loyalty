import { apiClient } from '@/shared/api/client-fetch';

export async function getSupplierSettings(supplierId) {
  try {
    return await apiClient.get(`/api/pricing/suppliers/${supplierId}/pricing`);
  } catch (err) {
    if (err?.status === 404) return null;
    throw err;
  }
}

export const upsertSupplierSettings = (supplierId, payload) =>
  apiClient.put(`/api/pricing/suppliers/${supplierId}/pricing`, payload);
