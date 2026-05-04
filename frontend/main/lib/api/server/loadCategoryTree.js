import "server-only";
import { cache } from "react";
import { cookies } from "next/headers";
import { mapCategoryTree } from "@/lib/format/mapCategoryTree";

const ACCESS_COOKIE = "lm_access_token";

function getBackendBaseUrl() {
  const raw = process.env.BACKEND_API_BASE_URL;
  if (!raw || typeof raw !== "string" || !raw.trim()) {
    throw new Error("Missing BACKEND_API_BASE_URL");
  }
  return raw.trim().replace(/\/+$/, "");
}

/**
 * Server-only loader for the catalog category tree with React `cache()`
 * deduplication across the RSC render pass plus Next.js fetch cache
 * (revalidate: 300s, tag: "category-tree") for cross-request reuse.
 *
 * @param {object} [opts]
 * @param {number} [opts.maxDepth] Optional max_depth (1..10)
 * @returns {Promise<Array<object>>} normalized tree (roots array, sorted)
 */
export const loadCategoryTree = cache(async (opts = {}) => {
  const base = getBackendBaseUrl();
  const sp = new URLSearchParams();
  const maxDepth = Number(opts?.maxDepth);
  if (Number.isInteger(maxDepth) && maxDepth >= 1 && maxDepth <= 10) {
    sp.set("max_depth", String(maxDepth));
  }

  const qs = sp.toString();
  const url = `${base}/api/v1/catalog/categories/tree${qs ? `?${qs}` : ""}`;

  let token = "";
  try {
    const jar = await cookies();
    token = jar.get(ACCESS_COOKIE)?.value || "";
  } catch {
    // outside request context — continue without auth
  }

  const headers = { accept: "application/json" };
  if (token) headers.authorization = `Bearer ${token}`;

  let res;
  try {
    res = await fetch(url, {
      headers,
      next: {
        revalidate: 300,
        tags: ["category-tree"],
      },
    });
  } catch (e) {
    if (process.env.NODE_ENV !== "production") {
      console.error("[loadCategoryTree] fetch failed", e);
    }
    return [];
  }

  if (!res.ok) {
    if (process.env.NODE_ENV !== "production") {
      const body = await res.text().catch(() => "");
      console.error(
        `[loadCategoryTree] upstream ${res.status}`,
        body.slice(0, 300),
      );
    }
    return [];
  }

  let raw;
  try {
    raw = await res.json();
  } catch {
    return [];
  }

  return mapCategoryTree(raw);
});
