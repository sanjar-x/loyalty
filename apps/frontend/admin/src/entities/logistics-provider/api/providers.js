import { apiClient } from '@/shared/api/clientFetch';

// Backend domain codes → operator-facing Russian copy. Code-keyed (not
// message-keyed): the codes are a stable contract while backend wording
// drifts between releases. `apiClient` applies these via `translationsByCode`.
const PROVIDER_TRANSLATIONS = {
  CONFLICT:
    'Для этого провайдера уже есть активный аккаунт. Сначала отключите его.',
  NOT_FOUND: 'Аккаунт не найден — возможно, удалён в другой вкладке.',
  PROVIDER_ACCOUNT_NOT_FOUND:
    'Аккаунт не найден — возможно, удалён в другой вкладке.',
  FORBIDDEN: 'Недостаточно прав: нужен доступ logistics:admin.',
};

const OPTS = { translationsByCode: PROVIDER_TRANSLATIONS };

function buildQuery(filters = {}) {
  const qs = new URLSearchParams();
  if (filters.providerCode) qs.set('providerCode', filters.providerCode);
  if (filters.onlyActive) qs.set('onlyActive', 'true');
  const s = qs.toString();
  return s ? `?${s}` : '';
}

/** List provider accounts. Returns the raw `{ items }` envelope. */
export function fetchProviderAccounts(filters) {
  return apiClient.get(`/api/logistics-providers${buildQuery(filters)}`, OPTS);
}

/** Single account — full `config` + `credentialFingerprints` for the edit form. */
export function fetchProviderAccount(id) {
  return apiClient.get(`/api/logistics-providers/${id}`, OPTS);
}

export function createProviderAccount(payload) {
  return apiClient.post('/api/providers', payload, OPTS);
}

export function updateProviderAccount(id, payload) {
  return apiClient.put(`/api/logistics-providers/${id}`, payload, OPTS);
}

export function setProviderAccountActive(id, isActive) {
  return apiClient.post(
    `/api/logistics-providers/${id}/active`,
    { isActive },
    OPTS,
  );
}

export function deleteProviderAccount(id) {
  return apiClient.del(`/api/logistics-providers/${id}`, OPTS);
}

/** Rebuild the backend's in-memory provider registry (task §6.3). */
export function refreshProviderRegistry() {
  return apiClient.post('/api/logistics-providers/refresh', undefined, OPTS);
}
