import { i18n } from '@/shared/lib/utils';
import { apiClient, ApiError } from '@/shared/api/clientFetch';
import { productCategoryTree } from '@/shared/mocks/productCategories';

const isDevelopment = process.env.NODE_ENV === 'development';

export async function fetchCategoryTree() {
  try {
    const data = await apiClient.get('/api/categories/tree');
    if (Array.isArray(data)) {
      // In production an empty tree is a valid backend answer — surface it
      // so the UI shows the empty state rather than silently swapping in
      // the dev mock fixture.
      if (data.length > 0 || !isDevelopment) return data;
    }
  } catch (err) {
    if (!(err instanceof ApiError)) throw err;
    // Production: bubble up so TanStack Query renders an error state.
    // Development: fall through to the local fixture so contributors can
    // keep working when the backend is down.
    if (!isDevelopment) throw err;
  }
  return productCategoryTree;
}

export function findCategoryPath(tree, rootId, groupId, leafId) {
  const root = tree.find((n) => n.id === rootId) ?? null;
  const group = root?.children?.find((n) => n.id === groupId) ?? null;
  const leaf = group?.children?.find((n) => n.id === leafId) ?? null;
  return { root, group, leaf };
}

/**
 * Walk the nested category tree (root → group → leaf) and return the first
 * node matching `id`, or `null`. Generic over arbitrary depth so it keeps
 * working if backend ever returns 4+ levels.
 */
export function findCategoryById(tree, id) {
  if (!id || !Array.isArray(tree)) return null;
  for (const node of tree) {
    if (node.id === id) return node;
    const child = findCategoryById(node.children, id);
    if (child) return child;
  }
  return null;
}

export function categoryLabel(node, fallback = 'Категория') {
  if (!node) return fallback;
  return i18n(node.nameI18N, node.label ?? fallback);
}
