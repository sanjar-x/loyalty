import { i18n } from '@/lib/utils';
import { productCategoryTree } from '@/data/productCategories';

/**
 * Fetch the full category tree from the client-side API route.
 * Falls back to local mock data if the API is unavailable.
 */
export async function fetchCategoryTree() {
  try {
    const res = await fetch('/api/categories/tree');
    if (res.ok) {
      const data = await res.json();
      if (Array.isArray(data) && data.length > 0) return data;
    }
  } catch {
    // network error — fall through to mock
  }
  return productCategoryTree;
}

/**
 * Walk the tree and find nodes at each level by id.
 */
export function findCategoryPath(tree, rootId, groupId, leafId) {
  const root = tree.find((n) => n.id === rootId) ?? null;
  const group = root?.children?.find((n) => n.id === groupId) ?? null;
  const leaf = group?.children?.find((n) => n.id === leafId) ?? null;
  return { root, group, leaf };
}

/**
 * Get the display label from a category node.
 */
export function categoryLabel(node, fallback = 'Категория') {
  if (!node) return fallback;
  return i18n(node.nameI18N, node.label ?? fallback);
}
