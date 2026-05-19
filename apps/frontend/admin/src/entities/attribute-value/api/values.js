import { apiClient } from '@/shared/api/clientFetch';

const VALUE_TRANSLATIONS = {
  ATTRIBUTE_VALUE_NOT_FOUND: 'Значение атрибута не найдено',
  ATTRIBUTE_VALUE_CODE_CONFLICT:
    'Значение с таким кодом уже существует у этого атрибута',
  ATTRIBUTE_VALUE_SLUG_CONFLICT:
    'Значение с таким slug уже существует у этого атрибута',
  ATTRIBUTE_VALUE_HAS_USAGES:
    'Значение используется SKU. Деактивируйте вместо удаления.',
};

const OPTS = { translationsByCode: VALUE_TRANSLATIONS };

export function fetchAttributeValues(
  attributeId,
  { offset = 0, limit = 200, isActive, valueGroup } = {},
) {
  const qs = new URLSearchParams({
    offset: String(offset),
    limit: String(limit),
  });
  if (isActive !== undefined && isActive !== null && isActive !== '') {
    qs.set('isActive', String(isActive));
  }
  if (valueGroup) qs.set('valueGroup', valueGroup);

  return apiClient.get(
    `/api/catalog/attributes/${attributeId}/values?${qs}`,
    OPTS,
  );
}

export function getAttributeValue(attributeId, valueId) {
  return apiClient.get(
    `/api/catalog/attributes/${attributeId}/values/${valueId}`,
    OPTS,
  );
}

export function createAttributeValue(attributeId, payload) {
  return apiClient.post(
    `/api/catalog/attributes/${attributeId}/values`,
    payload,
    OPTS,
  );
}

export function updateAttributeValue(attributeId, valueId, payload) {
  return apiClient.patch(
    `/api/catalog/attributes/${attributeId}/values/${valueId}`,
    payload,
    OPTS,
  );
}

export function deleteAttributeValue(attributeId, valueId) {
  return apiClient.del(
    `/api/catalog/attributes/${attributeId}/values/${valueId}`,
    OPTS,
  );
}

export function deactivateAttributeValue(attributeId, valueId) {
  return apiClient.post(
    `/api/catalog/attributes/${attributeId}/values/${valueId}/deactivate`,
    undefined,
    OPTS,
  );
}

export function activateAttributeValue(attributeId, valueId) {
  return apiClient.post(
    `/api/catalog/attributes/${attributeId}/values/${valueId}/activate`,
    undefined,
    OPTS,
  );
}

export function bulkAddAttributeValues(attributeId, items) {
  return apiClient.post(
    `/api/catalog/attributes/${attributeId}/values/bulk`,
    { items },
    OPTS,
  );
}

export function reorderAttributeValues(attributeId, items) {
  return apiClient.post(
    `/api/catalog/attributes/${attributeId}/values/reorder`,
    { items },
    OPTS,
  );
}
