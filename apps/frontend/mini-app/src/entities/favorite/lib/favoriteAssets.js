/**
 * Shared image-URL helpers for the Favorites pages.
 *
 * Previously each favorites page (`app/favorites/page.jsx`,
 * `app/favorites/brands/page.jsx`) kept its own local
 * `getBrandLogoCandidates` / `getProductPhotoCandidates` — as a result, bugs
 * (e.g. not understanding the mapStorefrontProduct shape) had to be fixed in
 * two places. This module is the single source of truth.
 *
 * Strategy: the backend returns asset URLs in different conventions across
 * endpoints — either a direct CDN URL, a relative path, or a resource-id
 * tag. Each helper combines every possible resolver variant and returns a
 * unique URL list for `<ImgWithFallback>` to try in order.
 */

import { buildBackendAssetUrl } from '@/shared/lib/url';
import { buildProductPhotoUrl } from '@/entities/product/lib/photoUrl';
import { buildBrandLogoUrl } from '@/entities/brand/lib/logoUrl';

function uniqStrings(arr) {
  const seen = new Set();
  const out = [];
  for (const v of arr) {
    const s = typeof v === 'string' ? v.trim() : '';
    if (!s || seen.has(s)) continue;
    seen.add(s);
    out.push(s);
  }
  return out;
}

/**
 * BrandResponse / FavoriteBrandCardResponse → URL candidates.
 *
 * In the backend BrandResponse it's `logoUrl` (camel) or `logo` (legacy);
 * the Favorites card uses `logo_url` (snake). We try all of them.
 *
 * **Important**: if `logo` is empty we do not return any URL — there is no
 * `/brands/{id}/logo` resolver on the backend, and a request to that URL
 * returns 404 → `<img>` shows the broken-image icon. The clean fallback
 * (letter-circle) is implemented at the UI level.
 */
export function getBrandLogoCandidates(brand) {
  if (!brand || typeof brand !== 'object') return [];
  const logo =
    typeof brand.logoUrl === 'string' && brand.logoUrl.trim()
      ? brand.logoUrl.trim()
      : typeof brand.logo_url === 'string' && brand.logo_url.trim()
        ? brand.logo_url.trim()
        : typeof brand.logo === 'string' && brand.logo.trim()
          ? brand.logo.trim()
          : '';

  if (!logo) return [];

  return uniqStrings([
    buildBrandLogoUrl(logo),
    buildBackendAssetUrl(logo),
    buildBackendAssetUrl(logo, ['media']),
    buildBackendAssetUrl(logo, ['static']),
    buildBackendAssetUrl(logo, ['uploads']),
  ]);
}

/**
 * Product image candidates. Sources (priority order):
 *  1. mapStorefrontProduct output: `image: string`, `images: string[]`
 *  2. FavoriteProductCardResponse: `main_image_url: string`
 *  3. Raw PDP/PLP: `media[].url`
 */
export function getProductPhotoCandidates(productLike) {
  if (!productLike || typeof productLike !== 'object') return [];

  const collected = [];
  if (typeof productLike.image === 'string') collected.push(productLike.image);
  if (typeof productLike.main_image_url === 'string') {
    collected.push(productLike.main_image_url);
  }
  if (
    productLike.image &&
    typeof productLike.image === 'object' &&
    typeof productLike.image.url === 'string'
  ) {
    collected.push(productLike.image.url);
  }

  if (Array.isArray(productLike.images)) {
    for (const u of productLike.images) {
      if (typeof u === 'string') collected.push(u);
      else if (u && typeof u === 'object' && typeof u.url === 'string') {
        collected.push(u.url);
      }
    }
  }
  if (Array.isArray(productLike.media)) {
    for (const m of productLike.media) {
      if (m && typeof m === 'object' && typeof m.url === 'string') {
        collected.push(m.url);
      }
    }
  }

  const raw = collected.find((s) => typeof s === 'string' && s.trim()) ?? '';
  if (!raw) return [];
  const trimmed = raw.trim();

  return uniqStrings([
    buildProductPhotoUrl(trimmed),
    buildBackendAssetUrl(trimmed, ['media']),
    buildBackendAssetUrl(trimmed, ['static']),
    buildBackendAssetUrl(trimmed, ['uploads']),
    buildBackendAssetUrl(trimmed),
    trimmed,
  ]);
}

/**
 * Mapper from a list of BrandResponses into a UI carousel item.
 * The `favoriteIdSet` parameter fills the `isFavorite` flag for each item.
 */
export function brandToCarouselItem(b, favoriteIdSet) {
  if (!b || typeof b !== 'object' || !b.id) return null;
  const candidates = getBrandLogoCandidates(b);
  return {
    id: b.id,
    name: b.name ?? '',
    image: candidates[0] || '',
    imageFallbacks: candidates.slice(1),
    isFavorite: favoriteIdSet?.has?.(b.id) ?? false,
  };
}
