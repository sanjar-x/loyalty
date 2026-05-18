/**
 * Shared product → UI card mapper.
 *
 * Single source-of-truth: different variants used to live in `app/page.jsx`,
 * `app/cart/page.jsx`, `app/product/[slug]/ProductPageClient.jsx` and other
 * places (each one differing on whether `slug` was present — which caused a
 * regression where the UUID was sent as the slug during PDP navigation and
 * produced a 404).
 *
 * In this module:
 *  - `getProductGallery(product)` — full media URLs
 *  - `mapProductCard(product, favoriteIds)` — the single UI card shape
 *
 * Price formatter — `formatRubFloat` (`./price`); previously a local
 * `formatRubPrice`, deduplicated (naming code review).
 * Photo candidates — module-private; an exported variant lives in `./favoriteAssets`.
 */

import { buildBackendAssetUrl } from '@/shared/lib/url';
import { buildProductPhotoUrl } from './photoUrl';
import { formatRubFloat } from '@/shared/lib/money';

function getProductPhotoCandidates(product) {
  const candidates = [];

  // New API: image is {url, imageVariants} object
  const imageObj = product?.image;
  if (imageObj && typeof imageObj === 'object' && imageObj.url) {
    candidates.push(imageObj.url);
  }

  const rawDirect =
    (typeof product?.image === 'string' ? product.image : '') ||
    (typeof product?.image_url === 'string' ? product.image_url : '') ||
    (typeof product?.photo === 'string' ? product.photo : '') ||
    (typeof product?.photo_url === 'string' ? product.photo_url : '');
  if (rawDirect && rawDirect.trim()) candidates.push(rawDirect.trim());

  const images = Array.isArray(product?.images) ? product.images : [];
  const first = images?.[0];
  const fromImages =
    typeof first === 'string'
      ? first
      : first && typeof first === 'object'
        ? (first.url ?? first.filename ?? first.file ?? first.path)
        : null;
  const raw = typeof fromImages === 'string' ? fromImages.trim() : '';
  if (raw) candidates.push(raw);

  const photos = Array.isArray(product?.photos) ? product.photos : [];
  const firstPhoto = photos?.[0];
  const fromPhotos =
    typeof firstPhoto === 'string'
      ? firstPhoto
      : firstPhoto && typeof firstPhoto === 'object'
        ? (firstPhoto.url ?? firstPhoto.filename ?? firstPhoto.file ?? firstPhoto.path)
        : null;
  const rawPhoto = typeof fromPhotos === 'string' ? fromPhotos.trim() : '';
  if (rawPhoto) candidates.push(rawPhoto);

  const uniq = Array.from(new Set(candidates.filter((x) => typeof x === 'string' && x.trim())));

  const out = [];
  for (const src of uniq) {
    out.push(
      buildProductPhotoUrl(src),
      buildBackendAssetUrl(src, ['media']),
      buildBackendAssetUrl(src, ['static']),
      buildBackendAssetUrl(src, ['uploads']),
      buildBackendAssetUrl(src)
    );
  }
  return out.filter((x) => typeof x === 'string' && x.trim());
}

export function getProductGallery(product) {
  // In the PDP / PLP response, `images` arrives as an array
  // (mapStorefrontProduct: `media[].url` -> `images`).
  const raw = Array.isArray(product?.images) ? product.images : [];
  const urls = [];
  for (const item of raw) {
    const u =
      typeof item === 'string'
        ? item
        : item && typeof item === 'object'
          ? (item.url ?? item.filename ?? item.file ?? item.path ?? '')
          : '';
    const trimmed = typeof u === 'string' ? u.trim() : '';
    if (!trimmed) continue;
    const built = buildProductPhotoUrl(trimmed) || buildBackendAssetUrl(trimmed);
    if (built && !urls.includes(built)) urls.push(built);
  }
  return urls;
}

function resolveBrandName(rawBrand, product) {
  if (rawBrand && typeof rawBrand === 'object') return rawBrand.name ?? '';
  if (typeof rawBrand === 'string') return rawBrand;
  return product?.brand_name ?? '';
}

function resolveServerFavorite(product) {
  if (typeof product?.is_favourite === 'boolean') return product.is_favourite;
  if (typeof product?.is_favorite === 'boolean') return product.is_favorite;
  if (typeof product?.isFavorite === 'boolean') return product.isFavorite;
  return null;
}

/**
 * @param {object} product Product object returned from the API
 * @param {Set<string|number>|null} favoriteIds — set of favorite ids
 * @returns {object|null} UI card shape, or `null` if id is missing
 */
export function mapProductCard(product, favoriteIds) {
  const id = product?.id;
  if (id == null) return null;

  const candidates = getProductPhotoCandidates(product);
  const image = candidates[0] || '';
  const imageFallbacks = candidates.slice(1);

  const galleryFromImages = getProductGallery(product);
  const gallery = galleryFromImages.length > 0 ? galleryFromImages : image ? [image] : [];

  const name = product?.name ?? product?.title ?? product?.product_name ?? product?.model ?? '';

  const deliveryRaw = typeof product?.delivery === 'string' ? product.delivery : '';
  const deliveryText = deliveryRaw.trim() ? `Доставка: ${deliveryRaw.trim()}` : '';

  const serverFavorite = resolveServerFavorite(product);
  const isFavorite = Boolean((serverFavorite ?? false) || (favoriteIds?.has?.(id) ?? false));

  // Price: a number, or a { amount (kopecks), currency } object
  const rawPrice = product?.price;
  const priceValue = rawPrice && typeof rawPrice === 'object' ? rawPrice.amount / 100 : rawPrice;

  // Brand: a string, or a { id, name, slug } object
  const brandName = resolveBrandName(product?.brand, product);

  // Slug — critical for PDP navigation. The backend requires
  // `/storefront/products/{slug}`; if a slug is missing we fall back to id,
  // but ideally — always a real slug.
  const slug =
    typeof product?.slug === 'string' && product.slug.trim() ? product.slug.trim() : String(id);

  return {
    id,
    slug,
    name: String(name || ''),
    price: formatRubFloat(priceValue),
    image,
    imageFallbacks,
    gallery,
    isFavorite,
    deliveryText,
    brand: brandName,
  };
}
