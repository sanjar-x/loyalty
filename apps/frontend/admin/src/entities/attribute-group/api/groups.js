import { apiClient } from '@/shared/api/clientFetch';

const GROUP_TRANSLATIONS = {
  ATTRIBUTE_GROUP_NOT_FOUND: 'Группа атрибутов не найдена',
  ATTRIBUTE_GROUP_CODE_CONFLICT: 'Группа с таким кодом уже существует',
  ATTRIBUTE_GROUP_HAS_ATTRIBUTES:
    'Группа содержит атрибуты — переназначьте их перед удалением.',
};

const OPTS = { translationsByCode: GROUP_TRANSLATIONS };

export function fetchAttributeGroups({ offset = 0, limit = 200 } = {}) {
  const qs = new URLSearchParams({
    offset: String(offset),
    limit: String(limit),
  });
  return apiClient.get(`/api/catalog/attribute-groups?${qs}`, OPTS);
}

export function getAttributeGroup(groupId) {
  return apiClient.get(`/api/catalog/attribute-groups/${groupId}`, OPTS);
}

export function createAttributeGroup(payload) {
  return apiClient.post('/api/catalog/attribute-groups', payload, OPTS);
}

export function updateAttributeGroup(groupId, payload) {
  return apiClient.patch(
    `/api/catalog/attribute-groups/${groupId}`,
    payload,
    OPTS,
  );
}

export function deleteAttributeGroup(groupId) {
  return apiClient.del(`/api/catalog/attribute-groups/${groupId}`, OPTS);
}
