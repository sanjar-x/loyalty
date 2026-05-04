/**
 * Shared product → UI card mapper.
 *
 * Bitta source-of-truth: `app/page.jsx`, `app/trash/page.jsx`,
 * `app/product/[slug]/ProductPageClient.jsx` va boshqa joylarda turli
 * variantlar yashagan edi (har birida `slug` bormi yoki yo'qmi farq qilardi
 * — natijada PDP navigatsiyada UUID slug deb yuborilib 404 oluvchi regression
 * yuzaga kelgan).
 *
 * Bu modulda:
 *  - `formatRubPrice(value)` — number → "1 234 ₽"
 *  - `getProductPhotoCandidates(product)` — primary + fallback URL'lar
 *  - `getProductGallery(product)` — to'liq media URL'lar
 *  - `mapProductCard(product, favoriteIds)` — yagona UI card shape
 */

import {
  buildBackendAssetUrl,
  buildProductPhotoUrl,
} from "./backendAssets";

export function formatRubPrice(value) {
  const n = Number(value);
  if (!Number.isFinite(n)) return "";
  const rounded = Math.trunc(n);
  const formatted = rounded.toString().replace(/\B(?=(\d{3})+(?!\d))/g, " ");
  return `${formatted} ₽`;
}

export function getProductPhotoCandidates(product) {
  const candidates = [];

  // New API: image is {url, imageVariants} object
  const imageObj = product?.image;
  if (imageObj && typeof imageObj === "object" && imageObj.url) {
    candidates.push(imageObj.url);
  }

  const rawDirect =
    (typeof product?.image === "string" ? product.image : "") ||
    (typeof product?.image_url === "string" ? product.image_url : "") ||
    (typeof product?.photo === "string" ? product.photo : "") ||
    (typeof product?.photo_url === "string" ? product.photo_url : "");
  if (rawDirect && rawDirect.trim()) candidates.push(rawDirect.trim());

  const images = Array.isArray(product?.images) ? product.images : [];
  const first = images?.[0];
  const fromImages =
    typeof first === "string"
      ? first
      : first && typeof first === "object"
        ? (first.url ?? first.filename ?? first.file ?? first.path)
        : null;
  const raw = typeof fromImages === "string" ? fromImages.trim() : "";
  if (raw) candidates.push(raw);

  const photos = Array.isArray(product?.photos) ? product.photos : [];
  const firstPhoto = photos?.[0];
  const fromPhotos =
    typeof firstPhoto === "string"
      ? firstPhoto
      : firstPhoto && typeof firstPhoto === "object"
        ? (firstPhoto.url ??
          firstPhoto.filename ??
          firstPhoto.file ??
          firstPhoto.path)
        : null;
  const rawPhoto = typeof fromPhotos === "string" ? fromPhotos.trim() : "";
  if (rawPhoto) candidates.push(rawPhoto);

  const uniq = Array.from(
    new Set(candidates.filter((x) => typeof x === "string" && x.trim())),
  );

  const out = [];
  for (const src of uniq) {
    out.push(
      buildProductPhotoUrl(src),
      buildBackendAssetUrl(src, ["media"]),
      buildBackendAssetUrl(src, ["static"]),
      buildBackendAssetUrl(src, ["uploads"]),
      buildBackendAssetUrl(src),
    );
  }
  return out.filter((x) => typeof x === "string" && x.trim());
}

export function getProductGallery(product) {
  // PDP / PLP response'da `images` array ko'rinishida keladi
  // (mapStorefrontProduct: `media[].url` -> `images`).
  const raw = Array.isArray(product?.images) ? product.images : [];
  const urls = [];
  for (const item of raw) {
    const u =
      typeof item === "string"
        ? item
        : item && typeof item === "object"
          ? (item.url ?? item.filename ?? item.file ?? item.path ?? "")
          : "";
    const trimmed = typeof u === "string" ? u.trim() : "";
    if (!trimmed) continue;
    const built =
      buildProductPhotoUrl(trimmed) || buildBackendAssetUrl(trimmed);
    if (built && !urls.includes(built)) urls.push(built);
  }
  return urls;
}

function resolveBrandName(rawBrand, product) {
  if (rawBrand && typeof rawBrand === "object") return rawBrand.name ?? "";
  if (typeof rawBrand === "string") return rawBrand;
  return product?.brand_name ?? "";
}

function resolveServerFavorite(product) {
  if (typeof product?.is_favourite === "boolean") return product.is_favourite;
  if (typeof product?.is_favorite === "boolean") return product.is_favorite;
  if (typeof product?.isFavorite === "boolean") return product.isFavorite;
  return null;
}

/**
 * @param {object} product API'dan kelgan mahsulot ob'ekti
 * @param {Set<string|number>|null} favoriteIds — sevimlilar to'plami
 * @returns {object|null} UI card shape, yoki id yo'q bo'lsa `null`
 */
export function mapProductCard(product, favoriteIds) {
  const id = product?.id;
  if (id == null) return null;

  const candidates = getProductPhotoCandidates(product);
  const image = candidates[0] || "";
  const imageFallbacks = candidates.slice(1);

  const galleryFromImages = getProductGallery(product);
  const gallery =
    galleryFromImages.length > 0
      ? galleryFromImages
      : image
        ? [image]
        : [];

  const name =
    product?.name ??
    product?.title ??
    product?.product_name ??
    product?.model ??
    "";

  const deliveryRaw =
    typeof product?.delivery === "string" ? product.delivery : "";
  const deliveryText = deliveryRaw.trim()
    ? `Доставка: ${deliveryRaw.trim()}`
    : "";

  const serverFavorite = resolveServerFavorite(product);
  const isFavorite = Boolean(
    (serverFavorite ?? false) || (favoriteIds?.has?.(id) ?? false),
  );

  // Price: number, yoki { amount (kopecks), currency } ob'ekti
  const rawPrice = product?.price;
  const priceValue =
    rawPrice && typeof rawPrice === "object" ? rawPrice.amount / 100 : rawPrice;

  // Brand: string, yoki { id, name, slug } ob'ekti
  const brandName = resolveBrandName(product?.brand, product);

  // Slug — PDP navigatsiyasi uchun kritik. Backend `/storefront/products/{slug}`
  // talab qiladi; slug yo'q bo'lsa id'ga fallback qilamiz, lekin ideal — har
  // doim haqiqiy slug.
  const slug =
    typeof product?.slug === "string" && product.slug.trim()
      ? product.slug.trim()
      : String(id);

  return {
    id,
    slug,
    name: String(name || ""),
    price: formatRubPrice(priceValue),
    image,
    imageFallbacks,
    gallery,
    isFavorite,
    deliveryText,
    brand: brandName,
  };
}
