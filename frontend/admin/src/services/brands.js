/**
 * Fetch all brands from the API.
 * Returns { items: BrandResponse[], total } or throws on failure.
 */
export async function fetchBrands() {
  const res = await fetch('/api/catalog/brands', {
    credentials: 'include',
  });
  if (!res.ok) {
    const error = new Error('Не удалось загрузить бренды');
    error.status = res.status;
    throw error;
  }
  return res.json();
}

/**
 * Group brands alphabetically by first letter of name.
 * Returns [{ key: 'A', brands: [...] }, ...]
 */
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
