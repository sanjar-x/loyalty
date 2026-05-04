const DEFAULT_LANG = "ru";

import {
  loadProductImageHint,
  saveProductImageHint,
} from "./productImageHints.js";

export function resolveI18N(i18nObj, fallback) {
  if (typeof i18nObj === "string") return i18nObj;
  if (i18nObj && typeof i18nObj === "object") {
    return (
      i18nObj[DEFAULT_LANG] ||
      i18nObj.en ||
      Object.values(i18nObj)[0] ||
      fallback ||
      ""
    );
  }
  return fallback || "";
}

/**
 * Normalizatsiya: StorefrontProductCardResponse / StorefrontProductDetailResponse
 * → legacy product shape (id, slug, name, price, image, images, brand, ...).
 * Shared between RTK Query transformResponse va Server Component loader.
 */
export function mapStorefrontProduct(p) {
  if (!p || typeof p !== "object") return null;

  const priceObj = p.price;
  const amount =
    priceObj && typeof priceObj === "object" ? priceObj.amount : priceObj;
  const compareAt =
    priceObj && typeof priceObj === "object" ? priceObj.compareAt : null;
  const priceNum = typeof amount === "number" ? amount / 100 : null;
  const oldPriceNum = typeof compareAt === "number" ? compareAt / 100 : null;

  const imageObj = p.image;
  let imageUrl =
    imageObj && typeof imageObj === "object"
      ? imageObj.url
      : typeof imageObj === "string"
        ? imageObj
        : "";

  const mediaImages = [];
  // PLP (StorefrontProductCardResponse): `images: StorefrontImageResponse[]`
  if (Array.isArray(p.images)) {
    for (const m of p.images) {
      const u =
        m && typeof m === "object"
          ? m.url
          : typeof m === "string"
            ? m
            : "";
      if (u && !mediaImages.includes(u)) mediaImages.push(u);
    }
  }
  // PDP (StorefrontProductDetailResponse): `media: MediaAsset[]`
  if (Array.isArray(p.media)) {
    for (const m of p.media) {
      const u =
        m && typeof m === "object"
          ? m.url
          : typeof m === "string"
            ? m
            : "";
      if (u && !mediaImages.includes(u)) mediaImages.push(u);
    }
  }

  if (!imageUrl && mediaImages.length) imageUrl = mediaImages[0];

  // Fallback: if backend returned empty media on PDP, reuse cached hints seeded
  // by PLP/similar/also-viewed responses (see productImageHints.js).
  const slugKey = typeof p.slug === "string" ? p.slug : "";
  if (!mediaImages.length && slugKey) {
    const hinted = loadProductImageHint(slugKey);
    if (hinted.length) {
      for (const u of hinted) mediaImages.push(u);
      if (!imageUrl) imageUrl = hinted[0];
    }
  } else if (mediaImages.length && slugKey) {
    saveProductImageHint(slugKey, mediaImages);
  }

  const brandObj = p.brand;
  const brandName =
    brandObj && typeof brandObj === "object"
      ? brandObj.name
      : typeof brandObj === "string"
        ? brandObj
        : "";

  // Breadcrumbs (BreadcrumbResponse: {labelI18N, slug, label}) — resolve label for display.
  const rawBreadcrumbs = Array.isArray(p.breadcrumbs) ? p.breadcrumbs : [];
  const breadcrumbs = rawBreadcrumbs
    .map((c) => {
      if (!c || typeof c !== "object") return null;
      const label = resolveI18N(c.labelI18N, c.label || c.name || "");
      const slug = typeof c.slug === "string" ? c.slug : "";
      if (!label && !slug) return null;
      return { label, slug, labelI18N: c.labelI18N || null };
    })
    .filter(Boolean);

  // Attributes (StorefrontAttributeValueResponse) — top-level PDP spec list.
  const rawAttributes = Array.isArray(p.attributes) ? p.attributes : [];
  const attributes = rawAttributes
    .map((a) => {
      if (!a || typeof a !== "object") return null;
      const attributeName = resolveI18N(
        a.attributeNameI18N,
        a.attributeName || a.attributeCode || "",
      );
      const value = resolveI18N(a.valueI18N, a.value || a.valueCode || "");
      if (!attributeName && !value) return null;
      return {
        attributeCode: a.attributeCode || "",
        attributeName,
        valueCode: a.valueCode || "",
        value,
        groupCode: a.groupCode || null,
        groupName: resolveI18N(a.groupNameI18N, a.groupName || ""),
        sortOrder: Number.isFinite(a.sortOrder) ? a.sortOrder : 0,
      };
    })
    .filter(Boolean)
    .sort((a, b) => a.sortOrder - b.sortOrder);

  // Variants + SKUs. Backend Spec §1: storefront — camelCase. Lekin
  // backend versiyalari snake_case ham qaytarishi mumkin (legacy yoki
  // serializer config drift), shuning uchun ikkala variantni o'qiymiz.
  const rawVariants = Array.isArray(p.variants)
    ? p.variants
    : Array.isArray(p.product_variants)
      ? p.product_variants
      : [];
  const variants = rawVariants.map((v) => {
    const nameI18N = v?.nameI18N || v?.name_i18n || null;
    const name = resolveI18N(nameI18N, v?.name || "");
    const skusRaw = Array.isArray(v?.skus) ? v.skus : [];
    const skus = skusRaw.map((s) => mapSku(s));
    return {
      id: v?.id,
      name,
      nameI18N,
      sortOrder: Number.isFinite(v?.sortOrder)
        ? v.sortOrder
        : Number.isFinite(v?.sort_order)
          ? v.sort_order
          : 0,
      skus,
    };
  });

  const flatSkus = [];
  for (const v of variants) for (const s of v.skus) flatSkus.push(s);

  // Default SKU: first active with lowest resolved price; else first sku.
  let defaultSku = null;
  for (const s of flatSkus) {
    if (!s || s.isActive === false) continue;
    if (!defaultSku) defaultSku = s;
    else if (
      typeof s.resolvedPrice === "number" &&
      typeof defaultSku.resolvedPrice === "number" &&
      s.resolvedPrice < defaultSku.resolvedPrice
    ) {
      defaultSku = s;
    }
  }
  if (!defaultSku && flatSkus.length) defaultSku = flatSkus[0];

  // Top-level price falls back to defaultSku.resolvedPrice when not provided.
  const finalPrice =
    typeof priceNum === "number" ? priceNum : defaultSku?.resolvedPrice ?? null;
  const finalCompareAt =
    typeof oldPriceNum === "number"
      ? oldPriceNum
      : defaultSku?.compareAtPrice ?? null;

  return {
    id: p.id,
    slug: p.slug || p.id,
    name: resolveI18N(p.titleI18N, p.title || p.name || ""),
    title: resolveI18N(p.titleI18N, p.title || p.name || ""),
    description: resolveI18N(p.descriptionI18N, p.description || ""),
    price: finalPrice,
    oldPrice: finalCompareAt,
    currency: priceObj?.currency || "RUB",
    image: imageUrl,
    images: mediaImages.length ? mediaImages : imageUrl ? [imageUrl] : [],
    brand: brandObj || brandName,
    brand_name: brandName,
    // Defensive: ikkala namespace'ga ham qaraymiz (camelCase canonical, lekin
    // snake_case backend drift uchun safe).
    in_stock: Boolean(p.inStock ?? p.in_stock),
    variantCount: p.variantCount ?? p.variant_count ?? 0,
    popularityScore: p.popularityScore ?? p.popularity_score ?? 0,
    publishedAt: p.publishedAt ?? p.published_at ?? null,
    breadcrumbs,
    variants,
    skus: flatSkus,
    defaultSku,
    attributes,
    tags: Array.isArray(p.tags) ? p.tags : [],
    version: p.version ?? null,
    _raw: p,
  };
}

/**
 * Clothing size token detection. Backend `variantAttributes` faqat UUID juftlik
 * sifatida keladi (label yo'q), shuning uchun `skuCode`'dan o'qiladigan label
 * qidiramiz — agar topilmasa `null` qaytariladi va sheet UI fallback'ga o'tadi.
 *
 * Qo'llab-quvvatlanuvchi shakllar:
 *   "BRAND-RED-XL"     → "XL"
 *   "TSHIRT_BLACK_M"   → "M"
 *   "JEANS-32"         → "32"
 *   "SHOES-EU42"       → "EU42"
 *   "ONE-SIZE"         → "ONE SIZE"
 */
const SIZE_TOKEN_RE = /^(?:XX{0,2}S|XS|S|M|L|XL|XX{0,2}L|XXXL|2XL|3XL|4XL|5XL|ONE[\s_-]?SIZE|OS|EU\d{2,3}|UK\d{1,2}|US\d{1,2}|\d{2,3})$/i;

function extractSizeFromSkuCode(skuCode) {
  if (typeof skuCode !== "string" || !skuCode.trim()) return null;
  const parts = skuCode.trim().split(/[-_/\s]+/).filter(Boolean);
  // Oxiridan boshlab tekshiramiz — odatda size suffiksda turadi.
  for (let i = parts.length - 1; i >= 0; i -= 1) {
    const tok = parts[i];
    if (SIZE_TOKEN_RE.test(tok)) {
      return tok.toUpperCase().replace(/[_-]/g, " ");
    }
  }
  return null;
}

// Normalize a single SKU: kopecks → rubles, keep UUIDs untouched.
// Defensive: backend ba'zan camelCase (skuCode), ba'zan snake_case (sku_code) uchun
// ikkala variantni o'qiymiz.
function mapSku(s) {
  if (!s || typeof s !== "object") return null;
  const toRub = (m) => {
    const amt =
      m && typeof m === "object" ? m.amount : typeof m === "number" ? m : null;
    return typeof amt === "number" ? amt / 100 : null;
  };
  const skuCode = s.skuCode || s.sku_code || "";
  const resolvedPriceObj = s.resolvedPrice ?? s.resolved_price ?? null;
  const compareAtObj = s.compareAtPrice ?? s.compare_at_price ?? null;
  const variantAttrsRaw = Array.isArray(s.variantAttributes)
    ? s.variantAttributes
    : Array.isArray(s.variant_attributes)
      ? s.variant_attributes
      : [];
  // Derived display label: clothing size token bo'lsa shu, aks holda
  // skuCode'ning oxirgi qismi (BRAND-RED-XL → XL), bo'lmasa qisqartirilgan UUID.
  const sizeToken = extractSizeFromSkuCode(skuCode);
  const fallbackTail = skuCode
    ? skuCode.split(/[-_/\s]+/).filter(Boolean).pop()?.toUpperCase()
    : "";
  const label =
    sizeToken ||
    fallbackTail ||
    (s.id ? String(s.id).slice(0, 4).toUpperCase() : "—");

  return {
    id: s.id,
    skuCode,
    label,
    price: toRub(s.price),
    resolvedPrice: toRub(resolvedPriceObj),
    compareAtPrice: toRub(compareAtObj),
    currency:
      resolvedPriceObj?.currency || s.price?.currency || "RUB",
    isActive: s.isActive ?? s.is_active ?? true,
    variantAttributes: variantAttrsRaw
      .map((va) =>
        va && typeof va === "object"
          ? {
              attributeId: va.attributeId || va.attribute_id || "",
              attributeValueId:
                va.attributeValueId || va.attribute_value_id || "",
              attributeCode: va.attributeCode || va.attribute_code || "",
              attributeName: va.attributeName ?? va.attribute_name ?? null,
              attributeNameI18N:
                va.attributeNameI18N ?? va.attribute_name_i18n ?? null,
              valueCode: va.valueCode || va.value_code || "",
              value: va.value ?? null,
              valueI18N: va.valueI18N ?? va.value_i18n ?? null,
              sortOrder:
                typeof va.sortOrder === "number"
                  ? va.sortOrder
                  : typeof va.sort_order === "number"
                    ? va.sort_order
                    : 0,
            }
          : null,
      )
      .filter(Boolean),
  };
}

export function unwrapPLPResponse(response) {
  const items = Array.isArray(response?.items)
    ? response.items
    : Array.isArray(response)
      ? response
      : [];
  return {
    items: items.map(mapStorefrontProduct).filter(Boolean),
    hasNext: Boolean(response?.hasNext),
    nextCursor: response?.nextCursor || null,
    total: response?.total ?? null,
    facets: response?.facets || null,
  };
}
