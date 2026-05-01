import { apiClient } from '@/shared/api/client-fetch';

export async function getCategorySettings(categoryId, contextId) {
  try {
    return await apiClient.get(
      `/api/pricing/categories/${categoryId}/pricing?context_id=${contextId}`,
    );
  } catch (err) {
    if (err?.status === 404) return null;
    throw err;
  }
}

export const upsertCategorySettings = (categoryId, contextId, payload) =>
  apiClient.put(
    `/api/pricing/categories/${categoryId}/pricing/${contextId}`,
    payload,
  );

export async function deleteCategorySettings(categoryId, contextId) {
  await apiClient.del(
    `/api/pricing/categories/${categoryId}/pricing/${contextId}`,
  );
  return true;
}
