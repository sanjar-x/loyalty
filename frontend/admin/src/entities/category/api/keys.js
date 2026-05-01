export const categoryKeys = {
  all: ['categories'],
  tree: () => [...categoryKeys.all, 'tree'],
  formAttributes: (categoryId) => [
    ...categoryKeys.all,
    'form-attributes',
    categoryId,
  ],
};
