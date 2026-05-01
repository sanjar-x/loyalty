import { apiClient } from '@/shared/api/client-fetch';

export const listContexts = () => apiClient.get('/api/pricing/contexts');

export const getContext = (id) => apiClient.get(`/api/pricing/contexts/${id}`);

export const createContext = (payload) =>
  apiClient.post('/api/pricing/contexts', payload);

export const updateContext = (id, patch) =>
  apiClient.patch(`/api/pricing/contexts/${id}`, patch);

export const deactivateContext = (id) =>
  apiClient.del(`/api/pricing/contexts/${id}`);

export const freezeContext = (id, { reason }) =>
  apiClient.post(`/api/pricing/contexts/${id}/freeze`, { reason });

export const unfreezeContext = (id) =>
  apiClient.post(`/api/pricing/contexts/${id}/unfreeze`);

export const getGlobalValues = (contextId) =>
  apiClient.get(`/api/pricing/contexts/${contextId}/variables/values`);

export const setGlobalValue = (
  contextId,
  variableCode,
  { value, versionLock },
) =>
  apiClient.put(
    `/api/pricing/contexts/${contextId}/variables/values/${variableCode}`,
    { value, version_lock: versionLock },
  );
