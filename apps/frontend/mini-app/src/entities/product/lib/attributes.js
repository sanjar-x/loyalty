/**
 * Utilities for working with product variant attributes, media, and sizes on PDP.
 */

const GALLERY_ROLES = new Set(['main', 'gallery', 'hover']);

/**
 * From MediaAssetResponse[], return gallery image URLs for a given variantId.
 * Includes product-level assets (variantId == null) as fallbacks.
 */
export function getGalleryImages(mediaAssets, variantId = null) {
  if (!Array.isArray(mediaAssets)) return [];

  const assets = mediaAssets
    .filter(
      (m) =>
        m &&
        typeof m === 'object' &&
        GALLERY_ROLES.has(m.role) &&
        typeof m.url === 'string' &&
        m.url.trim() &&
        (m.variantId === variantId || m.variantId == null)
    )
    .sort((a, b) => {
      const ar = a.role === 'main' ? -1 : 0;
      const br = b.role === 'main' ? -1 : 0;
      if (ar !== br) return ar - br;
      return (a.sortOrder ?? 0) - (b.sortOrder ?? 0);
    });

  const urls = [];
  const seen = new Set();
  for (const m of assets) {
    const u = m.url.trim();
    if (u && !seen.has(u)) {
      seen.add(u);
      urls.push(u);
    }
  }
  return urls;
}

/**
 * Return the first thumbnail image URL for a variant (for variant selector).
 * Prefers variant-scoped main/gallery; falls back to product-level.
 */
export function getVariantThumbnail(mediaAssets, variantId) {
  if (!Array.isArray(mediaAssets) || !variantId) return null;

  const variantAssets = mediaAssets
    .filter((m) => m && GALLERY_ROLES.has(m.role) && m.variantId === variantId && m.url?.trim())
    .sort((a, b) => {
      const ar = a.role === 'main' ? -1 : 0;
      const br = b.role === 'main' ? -1 : 0;
      if (ar !== br) return ar - br;
      return (a.sortOrder ?? 0) - (b.sortOrder ?? 0);
    });

  return variantAssets[0]?.url ?? null;
}

/**
 * Find a size_guide asset URL from media list (for size chart modal).
 */
export function getSizeGuideUrl(mediaAssets) {
  if (!Array.isArray(mediaAssets)) return null;
  const asset = mediaAssets.find((m) => m?.role === 'size_guide' && m.url?.trim());
  return asset?.url ?? null;
}

/**
 * Try to extract a human-readable size label from a SKU code.
 * e.g., "BRAND-PROD-M" → "M", "BRAND-40" → "40"
 */
export function parseSizeFromSkuCode(skuCode) {
  const s = String(skuCode ?? '').trim();

  // EU numeric sizes at the end: -38, -40, -42, etc.
  const numMatch = s.match(/[-_](3[4-9]|4\d|50)$/i);
  if (numMatch) return numMatch[1];

  // Alpha sizes at the end
  const alphaMatch = s.match(/[-_](XXS|XS|S|M|L|XL|XXL|XXXL)$/i);
  if (alphaMatch) return alphaMatch[1].toUpperCase();

  // Last dash-separated segment
  const parts = s.split(/[-_]/);
  const last = parts[parts.length - 1];
  return last || s;
}

// Find the size attribute inside a backend SKU's `variantAttributes`.
// Substring matching: the backend returns names like `size`, `clothing_size`,
// `shoe_size`, and Russian variants like `Размер`, `Размер одежды`, `Размер обуви`
// across various domains — a single check covers them all.
function findSizeAttribute(variantAttributes) {
  if (!Array.isArray(variantAttributes)) return null;

  const matches = (va) => {
    const code = typeof va?.attributeCode === 'string' ? va.attributeCode : '';
    if (code && code.toLowerCase().includes('size')) return true;

    const ru = va?.attributeNameI18N?.ru;
    const en = va?.attributeNameI18N?.en;
    const name = ru || en || va?.attributeName || '';
    if (typeof name !== 'string') return false;
    const lower = name.toLowerCase();
    return lower.includes('размер') || lower.includes('size');
  };

  return variantAttributes.find(matches) ?? null;
}

// Normalize a short alpha code for a size label: `"m"` → `"M"`.
// Numeric (`"42"`) and long strings (`"one size"`) are left untouched.
function normalizeSizeCode(code) {
  const s = typeof code === 'string' ? code.trim() : '';
  if (!s) return '';
  if (/^[a-z]{1,4}$/.test(s)) return s.toUpperCase();
  return s;
}

// Pick a visible label from the attribute pair:
// `value` (denormalized display) → `valueI18N.ru` → `valueI18N.en`
// → `valueCode` (uppercased).
function pickAttributeLabel(va) {
  if (!va) return '';
  if (typeof va.value === 'string' && va.value.trim()) return va.value.trim();
  const ru = va?.valueI18N?.ru;
  if (typeof ru === 'string' && ru.trim()) return ru.trim();
  const en = va?.valueI18N?.en;
  if (typeof en === 'string' && en.trim()) return en.trim();
  return normalizeSizeCode(va.valueCode);
}

/**
 * Derive a list of size options from a variant's SKUs.
 * Returns [{label, skuId, available, sortOrder}], deduped, sorted by backend
 * sortOrder when available.
 *
 * Priority for the label:
 *   1. SKU.variantAttributes — denormalized size attribute (value/valueI18N/valueCode).
 *   2. parseSizeFromSkuCode — fallback for legacy responses without denormalization.
 */
export function deriveSizesFromSkus(skus) {
  if (!Array.isArray(skus)) return [];

  const seen = new Set();
  const result = [];

  for (const sku of skus) {
    const sizeAttr = findSizeAttribute(sku?.variantAttributes);
    const attrLabel = pickAttributeLabel(sizeAttr);
    const label = attrLabel || parseSizeFromSkuCode(sku?.skuCode);
    if (!label || seen.has(label)) continue;
    seen.add(label);
    result.push({
      label,
      skuId: sku.id,
      available: sku.isActive !== false,
      sortOrder: typeof sizeAttr?.sortOrder === 'number' ? sizeAttr.sortOrder : null,
    });
  }

  // If sortOrder is present, sort by it (XS<S<M<L<XL); otherwise preserve original order.
  const hasSortOrder = result.some((r) => r.sortOrder != null);
  if (hasSortOrder) {
    result.sort((a, b) => {
      const ao = a.sortOrder ?? Number.MAX_SAFE_INTEGER;
      const bo = b.sortOrder ?? Number.MAX_SAFE_INTEGER;
      return ao - bo;
    });
  }

  return result;
}
