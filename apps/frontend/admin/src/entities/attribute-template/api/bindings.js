import { apiClient } from '@/shared/api/clientFetch';

const BINDING_TRANSLATIONS = {
  ATTRIBUTE_TEMPLATE_BINDING_DUPLICATE: 'Этот атрибут уже привязан к шаблону',
  ATTRIBUTE_TEMPLATE_BINDING_NOT_FOUND: 'Привязка не найдена',
};

const OPTS = { translationsByCode: BINDING_TRANSLATIONS };

export function fetchTemplateBindings(
  templateId,
  { offset = 0, limit = 500 } = {},
) {
  const qs = new URLSearchParams({
    offset: String(offset),
    limit: String(limit),
  });
  return apiClient.get(
    `/api/catalog/attribute-templates/${templateId}/attributes?${qs}`,
    OPTS,
  );
}

export function bindAttributeToTemplate(templateId, payload) {
  return apiClient.post(
    `/api/catalog/attribute-templates/${templateId}/attributes`,
    payload,
    OPTS,
  );
}

export function updateTemplateBinding(templateId, bindingId, payload) {
  return apiClient.patch(
    `/api/catalog/attribute-templates/${templateId}/attributes/${bindingId}`,
    payload,
    OPTS,
  );
}

export function unbindAttributeFromTemplate(templateId, bindingId) {
  return apiClient.del(
    `/api/catalog/attribute-templates/${templateId}/attributes/${bindingId}`,
    OPTS,
  );
}

export function reorderTemplateBindings(templateId, items) {
  return apiClient.post(
    `/api/catalog/attribute-templates/${templateId}/attributes/reorder`,
    { items },
    OPTS,
  );
}
