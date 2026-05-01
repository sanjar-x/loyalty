import { apiClient } from '@/shared/api/client-fetch';

/**
 * Storefront form-attributes for a leaf category — describes which fields
 * the product creation/edit form should render for this category.
 *
 * Lives in `entities/category` because the endpoint is keyed by category and
 * the response is metadata about the category itself, even though it's used
 * primarily by the product-form feature.
 */
export function fetchFormAttributes(categoryId) {
  if (!categoryId) return Promise.resolve(null);
  return apiClient.get(
    `/api/catalog/storefront/categories/${categoryId}/form-attributes`,
  );
}
