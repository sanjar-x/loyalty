import { apiClient } from '@/shared/api/client-fetch';

export function fetchBrands() {
  return apiClient.get('/api/catalog/brands');
}

export function createBrand(payload, opts) {
  return apiClient.post('/api/catalog/brands', payload, opts);
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
