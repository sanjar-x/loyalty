import { apiClient } from '@/shared/api/clientFetch';

export function listVersions(contextId, { status } = {}) {
  const qs = new URLSearchParams();
  if (status) qs.set('status', status);
  const tail = qs.toString() ? `?${qs}` : '';
  return apiClient.get(
    `/api/pricing/contexts/${contextId}/formula/versions${tail}`,
  );
}

export const getVersion = (contextId, versionId) =>
  apiClient.get(
    `/api/pricing/contexts/${contextId}/formula/versions/${versionId}`,
  );

export async function getDraft(contextId) {
  try {
    return await apiClient.get(
      `/api/pricing/contexts/${contextId}/formula/draft`,
    );
  } catch (err) {
    if (err?.status === 404) return null;
    throw err;
  }
}

export function saveDraft(contextId, { ast, expectedVersionLock }) {
  const body = { ast };
  if (expectedVersionLock != null)
    body.expectedVersionLock = expectedVersionLock;
  return apiClient.put(
    `/api/pricing/contexts/${contextId}/formula/draft`,
    body,
  );
}

export const deleteDraft = (contextId) =>
  apiClient.del(`/api/pricing/contexts/${contextId}/formula/draft`);

export const publishDraft = (contextId) =>
  apiClient.post(`/api/pricing/contexts/${contextId}/formula/draft/publish`);

export const rollbackVersion = (contextId, versionId) =>
  apiClient.post(
    `/api/pricing/contexts/${contextId}/formula/versions/${versionId}/rollback`,
  );

export function previewPrice({ productId, categoryId, contextId, supplierId }) {
  const body = { productId, categoryId, contextId };
  if (supplierId) body.supplierId = supplierId;
  return apiClient.post('/api/pricing/preview', body);
}
