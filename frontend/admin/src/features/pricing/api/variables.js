import { apiClient } from '@/shared/api/client-fetch';

export function listVariables({ scope, isSystem, isFxRate } = {}) {
  const params = new URLSearchParams();
  if (scope) params.set('scope', scope);
  if (isSystem !== undefined) params.set('is_system', String(isSystem));
  if (isFxRate !== undefined) params.set('is_fx_rate', String(isFxRate));
  const qs = params.toString();
  return apiClient.get(`/api/pricing/variables${qs ? `?${qs}` : ''}`);
}

export const getVariable = (id) =>
  apiClient.get(`/api/pricing/variables/${id}`);

export const createVariable = (payload) =>
  apiClient.post('/api/pricing/variables', payload);

export const updateVariable = (id, patch) =>
  apiClient.patch(`/api/pricing/variables/${id}`, patch);

export async function deleteVariable(id) {
  await apiClient.del(`/api/pricing/variables/${id}`);
  return true;
}
