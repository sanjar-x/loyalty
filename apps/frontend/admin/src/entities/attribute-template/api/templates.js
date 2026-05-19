import { apiClient } from '@/shared/api/clientFetch';

const TEMPLATE_TRANSLATIONS = {
  ATTRIBUTE_TEMPLATE_NOT_FOUND: 'Шаблон атрибутов не найден',
  ATTRIBUTE_TEMPLATE_CODE_CONFLICT: 'Шаблон с таким кодом уже существует',
  ATTRIBUTE_TEMPLATE_HAS_CATEGORIES:
    'Шаблон используется категориями. Сначала отвяжите его перед удалением.',
  ATTRIBUTE_TEMPLATE_BINDING_DUPLICATE: 'Этот атрибут уже привязан к шаблону.',
  ATTRIBUTE_TEMPLATE_BINDING_NOT_FOUND: 'Привязка не найдена',
};

const OPTS = { translationsByCode: TEMPLATE_TRANSLATIONS };

export function fetchAttributeTemplates({ offset = 0, limit = 200 } = {}) {
  const qs = new URLSearchParams({
    offset: String(offset),
    limit: String(limit),
  });
  return apiClient.get(`/api/catalog/attribute-templates?${qs}`, OPTS);
}

export function getAttributeTemplate(templateId) {
  return apiClient.get(`/api/catalog/attribute-templates/${templateId}`, OPTS);
}

export function createAttributeTemplate(payload) {
  return apiClient.post('/api/catalog/attribute-templates', payload, OPTS);
}

export function updateAttributeTemplate(templateId, payload) {
  return apiClient.patch(
    `/api/catalog/attribute-templates/${templateId}`,
    payload,
    OPTS,
  );
}

export function deleteAttributeTemplate(templateId) {
  return apiClient.del(`/api/catalog/attribute-templates/${templateId}`, OPTS);
}

export function cloneAttributeTemplate(payload) {
  return apiClient.post(
    '/api/catalog/attribute-templates/clone',
    payload,
    OPTS,
  );
}
