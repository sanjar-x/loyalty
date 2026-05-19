// Attribute values are scoped per parent attribute; the parent id is part
// of every key so a single qc.invalidateQueries call against the parent
// list refreshes only the relevant slice.
export const attributeValueKeys = {
  all: ['attribute-values'],
  byAttribute: (attributeId) => [...attributeValueKeys.all, attributeId],
  list: (attributeId, filters) => [
    ...attributeValueKeys.byAttribute(attributeId),
    'list',
    filters,
  ],
  detail: (attributeId, valueId) => [
    ...attributeValueKeys.byAttribute(attributeId),
    'detail',
    valueId,
  ],
};
