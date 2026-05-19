import { apiClient } from '@/shared/api/clientFetch';

const ATTRIBUTE_TRANSLATIONS = {
  ATTRIBUTE_NOT_FOUND: 'Атрибут не найден',
  ATTRIBUTE_SLUG_CONFLICT: 'Атрибут с таким slug уже существует',
  ATTRIBUTE_CODE_CONFLICT: 'Атрибут с таким кодом уже существует',
  ATTRIBUTE_HAS_USAGES:
    'Атрибут используется. Сначала отвяжите его от шаблонов и продуктов.',
  ATTRIBUTE_LEVEL_IMMUTABLE:
    'Уровень атрибута нельзя изменить — slug/code/data_type заморожены.',
};

const OPTS = { translationsByCode: ATTRIBUTE_TRANSLATIONS };

export function fetchAttributes(params = {}) {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== '') {
      search.set(key, String(value));
    }
  }
  const qs = search.toString();
  return apiClient.get(
    qs ? `/api/catalog/attributes?${qs}` : '/api/catalog/attributes',
    OPTS,
  );
}

export function getAttribute(attributeId) {
  return apiClient.get(`/api/catalog/attributes/${attributeId}`, OPTS);
}

export function createAttribute(payload) {
  return apiClient.post('/api/catalog/attributes', payload, OPTS);
}

export function updateAttribute(attributeId, payload) {
  return apiClient.patch(
    `/api/catalog/attributes/${attributeId}`,
    payload,
    OPTS,
  );
}

export function deleteAttribute(attributeId) {
  return apiClient.del(`/api/catalog/attributes/${attributeId}`, OPTS);
}

export function getAttributeUsage(attributeId) {
  return apiClient.get(`/api/catalog/attributes/${attributeId}/usage`, OPTS);
}

export function bulkCreateAttributes({ items, skipExisting = false }) {
  return apiClient.post(
    '/api/catalog/attributes/bulk',
    { items, skipExisting },
    OPTS,
  );
}
