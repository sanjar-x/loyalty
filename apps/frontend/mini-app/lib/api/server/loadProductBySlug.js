import 'server-only';
import { cache } from 'react';
import { cookies } from 'next/headers';
import { mapStorefrontProduct } from '@/lib/adapters/mapStorefrontProduct';

const ACCESS_COOKIE = 'lm_access_token';

function getBackendBaseUrl() {
  const raw = process.env.BACKEND_API_BASE_URL;
  if (!raw || typeof raw !== 'string' || !raw.trim()) {
    throw new Error('Missing BACKEND_API_BASE_URL');
  }
  return raw.trim().replace(/\/+$/, '');
}

/**
 * Server-only product loader with React cache() deduplication.
 * Forwards auth cookie for personalized fields (is_favorite, pricing).
 * Uses Next.js fetch cache with tag-based revalidation.
 *
 * @param {string} slug - product slug or ID
 * @returns {Promise<object|null>} mapped product shape, or null if 404
 */
export const loadProductBySlug = cache(async (slug) => {
  if (!slug || typeof slug !== 'string') return null;

  const base = getBackendBaseUrl();
  const url = `${base}/api/v1/catalog/storefront/products/${encodeURIComponent(slug)}`;

  let token = '';
  try {
    const jar = await cookies();
    token = jar.get(ACCESS_COOKIE)?.value || '';
  } catch {
    // ignore (running outside request context)
  }

  const headers = { accept: 'application/json' };
  if (token) headers.authorization = `Bearer ${token}`;

  let res;
  try {
    res = await fetch(url, {
      headers,
      next: {
        revalidate: 60,
        tags: [`product:${slug}`, 'product'],
      },
    });
  } catch (e) {
    if (process.env.NODE_ENV !== 'production') {
      console.error('[loadProductBySlug] fetch failed', e);
    }
    return null;
  }

  if (res.status === 404) return null;
  if (!res.ok) {
    const bodyText = await res.text().catch(() => '');
    if (process.env.NODE_ENV !== 'production') {
      console.error(
        `[loadProductBySlug] upstream ${res.status} for slug=${slug}`,
        bodyText.slice(0, 300)
      );
    }
    // 5xx → throw so error.jsx boundary handles it (with retry)
    // 4xx (other than 404) → treat as not found
    if (res.status >= 500) {
      const err = new Error(`Upstream ${res.status} while fetching product "${slug}"`);
      err.status = res.status;
      err.digest = `product_upstream_${res.status}`;
      throw err;
    }
    return null;
  }

  let raw;
  try {
    raw = await res.json();
  } catch {
    return null;
  }

  const mapped = mapStorefrontProduct(raw);
  return mapped || null;
});
