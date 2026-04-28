import { NextResponse } from 'next/server';
import { backendFetch } from '@/lib/api-client';
import { imageBackendFetch } from '@/lib/image-api-client';
import { getAccessToken } from '@/lib/auth';
import { getOrFetch } from '@/lib/server-cache';

const ALLOWED_PARAMS = [
  'offset',
  'limit',
  'status',
  'brand_id',
  'sort_by',
  'published_after',
];

// Cache TTL for rarely-changing catalog metadata (5 minutes)
const LOOKUP_TTL_MS = 5 * 60 * 1000;
const ATTR_TTL_MS = 5 * 60 * 1000;

// ---------------------------------------------------------------------------
// Helpers — parallel enrichment for each product in the list
// ---------------------------------------------------------------------------

async function fetchProductMedia(token, productId) {
  // List view only shows the main thumbnail, so limit=1 is enough.
  const { ok, data } = await backendFetch(
    `/api/v1/catalog/products/${productId}/media?limit=1`,
    { headers: { Authorization: `Bearer ${token}` } },
  );

  if (!ok) {
    return [];
  }

  return data?.items ?? [];
}

async function fetchLookupData(token) {
  const [brands, categoryTree, suppliers] = await Promise.all([
    getOrFetch('catalog:brands', LOOKUP_TTL_MS, async () => {
      const res = await backendFetch('/api/v1/catalog/brands?offset=0&limit=200', {
        headers: { Authorization: `Bearer ${token}` },
      });
      return res.ok && res.data?.items ? res.data.items : [];
    }),
    getOrFetch('catalog:categories:tree', LOOKUP_TTL_MS, async () => {
      const res = await backendFetch('/api/v1/catalog/categories/tree', {
        headers: { Authorization: `Bearer ${token}` },
      });
      return res.ok && Array.isArray(res.data) ? res.data : [];
    }),
    getOrFetch('catalog:suppliers', LOOKUP_TTL_MS, async () => {
      const res = await backendFetch('/api/v1/suppliers?offset=0&limit=200', {
        headers: { Authorization: `Bearer ${token}` },
      });
      return res.ok && res.data?.items ? res.data.items : [];
    }),
  ]);

  return { brands, categoryTree, suppliers };
}

function buildBrandMap(brands) {
  const map = {};
  for (const b of brands) map[b.id] = b.name;
  return map;
}

function buildCategoryMap(tree, map = {}) {
  for (const node of tree) {
    map[node.id] = node.nameI18N ?? { ru: node.slug };
    if (node.children?.length) buildCategoryMap(node.children, map);
  }
  return map;
}

function buildSupplierMap(suppliers) {
  const map = {};
  for (const s of suppliers) map[s.id] = { type: s.type, countryCode: s.countryCode };
  return map;
}

/** Extract URL from main-backend MediaAssetResponse fields */
function extractUrlFromAsset(asset) {
  if (asset.url) return asset.url;
  if (asset.imageVariants?.length) {
    const v = asset.imageVariants.find((iv) => iv.url);
    if (v) return v.url;
  }
  return null;
}

/**
 * Resolve thumbnail URL for a product's media.
 * 1) Try extracting from main-backend MediaAssetResponse (url / imageVariants)
 * 2) Fallback: query image-backend by storageObjectId to get processed URLs
 */
async function resolveMainImageUrl(mediaItems) {
  if (!mediaItems?.length) return null;

  // Prefer "main" role, fall back to first item
  const mainAsset = mediaItems.find((m) => m.role === 'main') ?? mediaItems[0];

  // Step 1 — direct URL from main backend
  const directUrl = extractUrlFromAsset(mainAsset);
  if (directUrl) return directUrl;

  // Try any other media item
  for (const m of mediaItems) {
    const url = extractUrlFromAsset(m);
    if (url) return url;
  }

  // Step 2 — resolve from image backend using storageObjectId
  const storageId = mainAsset.storageObjectId ?? mediaItems.find((m) => m.storageObjectId)?.storageObjectId;
  if (storageId) {
    try {
      const { ok, data } = await imageBackendFetch(`/api/v1/media/${storageId}`);
      if (ok && data) {
        if (data.url) return data.url;
        if (data.variants?.length) {
          // Prefer smallest variant for thumbnail
          const sorted = [...data.variants].sort((a, b) => a.width - b.width);
          return sorted[0]?.url ?? null;
        }
      }
    } catch {
      // Image backend unavailable — graceful degradation
    }
  }

  return null;
}

/**
 * Collect unique attributeIds from all products' SKU variantAttributes.
 */
function collectAttributeIds(products) {
  const ids = new Set();
  for (const product of products) {
    if (!product?.variants) continue;
    for (const v of product.variants) {
      for (const sku of v.skus ?? []) {
        for (const va of sku.variantAttributes ?? []) {
          if (va.attributeId) ids.add(va.attributeId);
        }
      }
    }
  }
  return ids;
}

/**
 * Fetch attribute metadata + values for a set of attributeIds.
 * Each attrId is cached independently so repeated pages reuse prior fetches.
 * Returns { attrMeta: { [attrId]: nameRu }, valueMap: { [valueId]: { attrId, label } } }
 */
async function fetchAttributeLookup(token, attributeIds) {
  const attrMeta = {};
  const valueMap = {};
  if (!attributeIds.size) return { attrMeta, valueMap };

  const results = await Promise.all(
    [...attributeIds].map((attrId) =>
      getOrFetch(`catalog:attribute:${attrId}`, ATTR_TTL_MS, async () => {
        const [attrRes, valuesRes] = await Promise.all([
          backendFetch(`/api/v1/catalog/attributes/${attrId}`, {
            headers: { Authorization: `Bearer ${token}` },
          }),
          backendFetch(`/api/v1/catalog/attributes/${attrId}/values?offset=0&limit=200`, {
            headers: { Authorization: `Bearer ${token}` },
          }),
        ]);
        const attrName = attrRes.ok
          ? (attrRes.data?.nameI18N?.ru ?? attrRes.data?.code ?? attrId)
          : attrId;
        const values = valuesRes.ok && valuesRes.data?.items ? valuesRes.data.items : [];
        return { attrId, attrName, values };
      }),
    ),
  );

  for (const { attrId, attrName, values } of results) {
    attrMeta[attrId] = attrName;
    for (const v of values) {
      const label = v.valueI18N?.ru ?? v.code ?? v.slug;
      if (label) valueMap[v.id] = { attrId, label };
    }
  }

  return { attrMeta, valueMap };
}

/**
 * Extract variant attributes grouped by attribute name.
 * Returns array of { name: "Размер", values: ["EU 37", "EU 38"] }
 */
function extractVariantAttributes(product, attrMeta, valueMap) {
  if (!product?.variants?.length) return [];

  // Group: attrId → Set of valueIds
  const groups = {};
  for (const v of product.variants) {
    for (const sku of v.skus ?? []) {
      for (const va of sku.variantAttributes ?? []) {
        const entry = valueMap[va.attributeValueId];
        if (!entry) continue;
        if (!groups[entry.attrId]) groups[entry.attrId] = new Set();
        groups[entry.attrId].add(va.attributeValueId);
      }
    }
  }

  return Object.entries(groups).map(([attrId, valueIds]) => ({
    name: attrMeta[attrId] ?? attrId,
    values: [...valueIds].map((vid) => valueMap[vid]?.label).filter(Boolean),
  }));
}

async function enrichProduct(item, media, brandMap, categoryMap, supplierMap, attrMeta, valueMap) {
  const image = await resolveMainImageUrl(media);
  const brandName = brandMap[item.brandId] ?? null;
  const categoryI18N = categoryMap[item.primaryCategoryId] ?? null;

  const supplier = item?.supplierId ? supplierMap[item.supplierId] ?? null : null;

  const variantsCount = item?.variants?.length ?? 1;

  // Price from ProductResponse.minPrice (kopecks) or first variant/SKU
  let minPrice = item?.minPrice ?? null;
  let priceCurrency = item?.priceCurrency ?? 'RUB';

  // Fallback: try first variant's first SKU resolvedPrice
  if (minPrice == null && item?.variants?.length) {
    for (const v of item.variants) {
      if (v.defaultPrice?.amount != null) {
        minPrice = v.defaultPrice.amount;
        priceCurrency = v.defaultPrice.currency ?? 'RUB';
        break;
      }
      for (const sku of v.skus ?? []) {
        const p = sku.resolvedPrice ?? sku.price;
        if (p?.amount != null) {
          minPrice = p.amount;
          priceCurrency = p.currency ?? 'RUB';
          break;
        }
      }
      if (minPrice != null) break;
    }
  }

  const variantAttrs = extractVariantAttributes(item, attrMeta, valueMap);

  return {
    ...item,
    image,
    brandName,
    categoryI18N,
    variantsCount,
    variantAttrs,
    minPrice,
    priceCurrency,
    sourceUrl: item?.sourceUrl ?? null,
    supplierType: supplier?.type ?? null,
    supplierCountry: supplier?.countryCode ?? null,
  };
}

// ---------------------------------------------------------------------------
// GET — enriched product list
// ---------------------------------------------------------------------------

export async function GET(request) {
  const token = await getAccessToken();
  if (!token) {
    return NextResponse.json(
      { error: { code: 'UNAUTHORIZED', message: 'Not authenticated', details: {} } },
      { status: 401 },
    );
  }

  const { searchParams } = new URL(request.url);
  const params = new URLSearchParams();
  for (const key of ALLOWED_PARAMS) {
    const val = searchParams.get(key);
    if (val != null) params.set(key, val);
  }

  const qs = params.toString();
  const listPath = `/api/v1/catalog/products${qs ? `?${qs}` : ''}`;

  // 1) Fetch list + lookup data in parallel
  const [listRes, lookup] = await Promise.all([
    backendFetch(listPath, { headers: { Authorization: `Bearer ${token}` } }),
    fetchLookupData(token),
  ]);

  if (!listRes.ok) {
    return NextResponse.json(
      listRes.data ?? {
        error: { code: 'SERVICE_UNAVAILABLE', message: 'Backend unavailable', details: {} },
      },
      { status: listRes.status || 502 },
    );
  }

  const listData = listRes.data;
  const items = listData.items ?? [];

  const brandMap = buildBrandMap(lookup.brands);
  const categoryMap = buildCategoryMap(lookup.categoryTree);
  const supplierMap = buildSupplierMap(lookup.suppliers);

  // 2) Fetch media per product in parallel (list already contains variants/attrs/minPrice).
  const mediaByProduct = await Promise.all(
    items.map((item) => fetchProductMedia(token, item.id)),
  );

  // 3) Resolve variant attribute labels (sizes, colors, etc.) — cached per attrId.
  const attributeIds = collectAttributeIds(items);
  const { attrMeta, valueMap } = await fetchAttributeLookup(token, attributeIds);

  // 4) Enrich products with all resolved data
  const enriched = await Promise.all(
    items.map((item, i) =>
      enrichProduct(item, mediaByProduct[i], brandMap, categoryMap, supplierMap, attrMeta, valueMap),
    ),
  );

  return NextResponse.json({
    ...listData,
    items: enriched,
    _lookup: {
      brands: lookup.brands,
    },
  });
}

export async function POST(request) {
  const token = await getAccessToken();
  if (!token) {
    return NextResponse.json(
      { error: { code: 'UNAUTHORIZED', message: 'Not authenticated', details: {} } },
      { status: 401 },
    );
  }

  const body = await request.json();

  const { ok, status, data } = await backendFetch('/api/v1/catalog/products', {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

  if (!ok) {
    return NextResponse.json(
      data ?? { error: { code: 'SERVICE_UNAVAILABLE', message: 'Backend unavailable', details: {} } },
      { status: status || 502 },
    );
  }

  return NextResponse.json(data, { status: 201 });
}
