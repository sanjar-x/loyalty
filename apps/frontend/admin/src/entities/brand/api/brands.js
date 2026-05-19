import { apiClient } from '@/shared/api/clientFetch';

const BRAND_TRANSLATIONS = {
  BRAND_NOT_FOUND: 'Бренд не найден',
  BRAND_SLUG_CONFLICT: 'Бренд с таким slug уже существует',
  BRAND_HAS_PRODUCTS:
    'У бренда есть привязанные товары. Сначала переназначьте их на другой бренд.',
};

const BRAND_OPTS = { translationsByCode: BRAND_TRANSLATIONS };

export function fetchBrands() {
  return apiClient.get('/api/catalog/brands', BRAND_OPTS);
}

export function getBrand(brandId) {
  return apiClient.get(`/api/catalog/brands/${brandId}`, BRAND_OPTS);
}

export function createBrand(payload, opts) {
  return apiClient.post('/api/catalog/brands', payload, opts ?? BRAND_OPTS);
}

export function updateBrand(brandId, payload) {
  return apiClient.patch(`/api/catalog/brands/${brandId}`, payload, BRAND_OPTS);
}

export function deleteBrand(brandId) {
  return apiClient.del(`/api/catalog/brands/${brandId}`, BRAND_OPTS);
}

export function bulkCreateBrands(items) {
  return apiClient.post('/api/catalog/brands/bulk', { items }, BRAND_OPTS);
}

export function groupBrandsByLetter(brands) {
  const map = new Map();

  for (const brand of brands) {
    const letter = (brand.name?.[0] ?? '#').toUpperCase();
    if (!map.has(letter)) map.set(letter, []);
    map.get(letter).push(brand);
  }

  return Array.from(map.entries())
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([key, items]) => ({ key, brands: items }));
}
