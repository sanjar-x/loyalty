/**
 * Favorites sahifalari uchun shared image-URL helperlari.
 *
 * Eski holatda har bir favorites sahifasi (`app/favorites/page.jsx`,
 * `app/favorites/brands/page.jsx`) o'z lokal `getBrandLogoCandidates` /
 * `getProductPhotoCandidates` funksiyalarini saqlab kelgan — natijada bug
 * (e.g. mapStorefrontProduct shape'ni tushunmaslik) ikkita joyda alohida
 * tuzalardi. Bu modul yagona manba.
 *
 * Strategiya: backend turli endpointlarda asset URL'larni turli
 * konvensiyalarda qaytaradi — to'g'ridan-to'g'ri CDN URL, yoki nisbiy path,
 * yoki resource-id tag. Har bir helper barcha mumkin bo'lgan resolver
 * variantlarini birlashtirib, `<ImgWithFallback>` ketma-ket urinishi uchun
 * unique URL ro'yxatini qaytaradi.
 */

import {
  buildBackendAssetUrl,
  buildBrandLogoUrl,
  buildProductPhotoUrl,
} from '@/lib/url/backendAssets';

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
 * BrandResponse / FavoriteBrandCardResponse → URL kandidatlari.
 *
 * Backend BrandResponse'da `logoUrl` (camel) yoki `logo` (legacy);
 * Favorites cardda `logo_url` (snake). Hammasini sinab ko'ramiz.
 *
 * **Muhim**: `logo` bo'sh bo'lsa hech qanday URL qaytarmaymiz — backendda
 * `/brands/{id}/logo` resolver yo'q, va o'sha URL'ga so'rov 404 qaytaradi
 * → `<img>` brauzerda broken-image ikonkasini ko'rsatadi. Toza fallback
 * (letter-circle) UI darajasida amalga oshiriladi.
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
 * Mahsulot rasm kandidatlari. Manbalar (priority order):
 *  1. mapStorefrontProduct natijasi: `image: string`, `images: string[]`
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
 * BrandResponse'lar ro'yxatidan UI carousel itemiga ko'chiruvchi mapper.
 * `favoriteIdSet` parametri orqali har item'ning `isFavorite` flagi
 * to'ldiriladi.
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
