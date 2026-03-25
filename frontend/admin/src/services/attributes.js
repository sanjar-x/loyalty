/**
 * Fetch form attributes for a category.
 * Returns StorefrontFormResponse: { categoryId, groups: [...] }
 */
export async function fetchFormAttributes(categoryId) {
  if (!categoryId) return null;

  try {
    const res = await fetch(
      `/api/catalog/storefront/categories/${categoryId}/form-attributes`,
    );
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}
