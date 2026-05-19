export const attributeGroupKeys = {
  all: ['attribute-groups'],
  lists: () => [...attributeGroupKeys.all, 'list'],
  list: (filters) => [...attributeGroupKeys.lists(), filters],
  details: () => [...attributeGroupKeys.all, 'detail'],
  detail: (groupId) => [...attributeGroupKeys.details(), groupId],
};
