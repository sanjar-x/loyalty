export const attributeTemplateKeys = {
  all: ['attribute-templates'],
  lists: () => [...attributeTemplateKeys.all, 'list'],
  list: (filters) => [...attributeTemplateKeys.lists(), filters],
  details: () => [...attributeTemplateKeys.all, 'detail'],
  detail: (templateId) => [...attributeTemplateKeys.details(), templateId],
  bindings: (templateId) => [
    ...attributeTemplateKeys.detail(templateId),
    'bindings',
  ],
};
