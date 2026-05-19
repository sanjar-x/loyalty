import { apiClient } from '@/shared/api/clientFetch';

export const listMappings = () =>
  apiClient.get('/api/pricing/supplier-type-mapping');

export async function getMapping(supplierType) {
  try {
    return await apiClient.get(
      `/api/pricing/supplier-type-mapping/${supplierType}`,
    );
  } catch (err) {
    if (err?.status === 404) return null;
    throw err;
  }
}

export const upsertMapping = (supplierType, { contextId }) =>
  apiClient.put(`/api/pricing/supplier-type-mapping/${supplierType}`, {
    contextId,
  });

export async function deleteMapping(supplierType) {
  await apiClient.del(`/api/pricing/supplier-type-mapping/${supplierType}`);
  return true;
}
