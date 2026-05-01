import { backendFetch } from '@/shared/api/api-client';
import { getAccessToken } from '@/shared/auth/cookies';
import { productCategoryTree } from '@/shared/mocks/productCategories';

/**
 * Server-side: fetch category tree directly from the backend.
 * Used in Server Components where relative URLs don't work.
 */
export async function fetchCategoryTreeServer() {
  try {
    const token = await getAccessToken();
    const headers = token ? { Authorization: `Bearer ${token}` } : {};
    const { ok, data } = await backendFetch('/api/v1/catalog/categories/tree', {
      headers,
    });

    if (ok && Array.isArray(data) && data.length > 0) return data;
  } catch {
    // fall through to mock
  }
  return productCategoryTree;
}
