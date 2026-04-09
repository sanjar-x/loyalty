/**
 * Fetch form attributes for a category.
 * Returns StorefrontFormResponse: { categoryId, groups: [...] }
 * Throws on network/server errors for proper error handling upstream.
 */
export async function fetchFormAttributes(categoryId) {
  if (!categoryId) return null;

  const res = await fetch(
    `/api/catalog/storefront/categories/${categoryId}/form-attributes`,
    { credentials: 'include' },
  );
  if (!res.ok) {
    const error = new Error('Не удалось загрузить атрибуты формы');
    error.status = res.status;
    throw error;
  }
  return res.json();
}
