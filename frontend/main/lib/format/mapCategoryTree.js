import { resolveI18N } from "@/lib/format/mapStorefrontProduct";

/**
 * Normalize a single CategoryTreeResponse node (recursively) into a UI-friendly
 * shape. Keeps canonical fields (id, slug, fullSlug, level, sortOrder) and adds
 * a resolved `name` from `nameI18N`.
 *
 * @param {any} node CategoryTreeResponse from backend
 * @returns {object|null}
 */
export function mapCategoryNode(node) {
  if (!node || typeof node !== "object") return null;

  const id = typeof node.id === "string" ? node.id : null;
  const slug = typeof node.slug === "string" ? node.slug : "";
  const fullSlug =
    typeof node.fullSlug === "string" && node.fullSlug
      ? node.fullSlug
      : slug;
  const level = Number.isFinite(node.level) ? node.level : 0;
  const sortOrder = Number.isFinite(node.sortOrder) ? node.sortOrder : 0;
  const name = resolveI18N(node.nameI18N, node.name || slug || "");

  const rawChildren = Array.isArray(node.children) ? node.children : [];
  const children = rawChildren
    .map((c) => mapCategoryNode(c))
    .filter(Boolean)
    .sort((a, b) => a.sortOrder - b.sortOrder);

  if (!id || !slug) return null;

  return {
    id,
    slug,
    fullSlug,
    level,
    sortOrder,
    name,
    nameI18N: node.nameI18N && typeof node.nameI18N === "object" ? node.nameI18N : {},
    children,
  };
}

/**
 * Map the full tree payload (array of roots).
 */
export function mapCategoryTree(payload) {
  const arr = Array.isArray(payload) ? payload : [];
  return arr
    .map((n) => mapCategoryNode(n))
    .filter(Boolean)
    .sort((a, b) => a.sortOrder - b.sortOrder);
}

/**
 * Walk the tree and yield every node (depth-first, parents before children).
 */
export function walkCategoryTree(tree, visit) {
  const list = Array.isArray(tree) ? tree : [];
  for (const node of list) {
    if (!node) continue;
    visit(node);
    if (Array.isArray(node.children) && node.children.length) {
      walkCategoryTree(node.children, visit);
    }
  }
}

/**
 * Find a category node by its fullSlug (e.g. "odezhda/bombery").
 * Returns { node, trail } where trail is the ancestor chain (root → … → node).
 */
export function findByFullSlug(tree, fullSlug) {
  if (!fullSlug || typeof fullSlug !== "string") return null;

  const target = fullSlug.replace(/^\/+|\/+$/g, "");
  if (!target) return null;

  const list = Array.isArray(tree) ? tree : [];

  function dfs(nodes, trail) {
    for (const node of nodes) {
      if (!node) continue;
      const currentTrail = [...trail, node];
      if (node.fullSlug === target) {
        return { node, trail: currentTrail };
      }
      if (Array.isArray(node.children) && node.children.length) {
        const hit = dfs(node.children, currentTrail);
        if (hit) return hit;
      }
    }
    return null;
  }

  return dfs(list, []);
}

/**
 * Build the fullSlug value from an array of path segments (`["odezhda", "bombery"]`).
 * Falsy/empty segments are filtered out and the result is joined with "/".
 */
export function joinPathSegments(segments) {
  const arr = Array.isArray(segments) ? segments : [];
  return arr
    .map((s) => (typeof s === "string" ? s : ""))
    .map((s) => s.trim())
    .filter(Boolean)
    .join("/");
}
