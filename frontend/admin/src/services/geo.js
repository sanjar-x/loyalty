/**
 * Fetch countries from the Geo API.
 *
 * @param {{ lang?: string, limit?: number }} [opts]
 * @returns {Promise<{ items: Array<{ code: string, name: string }>, total: number }>}
 */
export async function fetchCountries({ lang = 'ru', limit = 300 } = {}) {
  const qs = new URLSearchParams({ lang, limit: String(limit) });

  const res = await fetch(`/api/geo/countries?${qs}`, {
    credentials: 'include',
  });

  if (!res.ok) {
    const error = new Error('Не удалось загрузить список стран');
    error.status = res.status;
    throw error;
  }

  const data = await res.json();

  const items = (data.items ?? []).map((c) => {
    const tr = (c.translations ?? []).find((t) => t.lang_code === lang);
    return {
      code: c.alpha2,
      name: tr?.name ?? c.alpha2,
    };
  });

  // Sort alphabetically by name
  items.sort((a, b) => a.name.localeCompare(b.name, 'ru'));

  return { items, total: data.total ?? items.length };
}

/**
 * Fetch subdivisions (regions) for a country.
 *
 * @param {string} countryCode – ISO 3166-1 alpha-2 (e.g. "RU", "CN")
 * @param {{ lang?: string, search?: string, limit?: number }} [opts]
 * @returns {Promise<{ items: Array<{ code: string, name: string }>, total: number }>}
 */
export async function fetchSubdivisions(countryCode, { lang = 'ru', search = '', limit = 50 } = {}) {
  const qs = new URLSearchParams({ lang, limit: String(limit) });
  if (search) qs.set('search', search);

  const res = await fetch(`/api/geo/subdivisions/${encodeURIComponent(countryCode)}?${qs}`, {
    credentials: 'include',
  });

  if (!res.ok) {
    // Country not found in geo DB — treat as empty list, not an error
    if (res.status === 404) {
      return { items: [], total: 0, notFound: true };
    }
    const error = new Error('Не удалось загрузить регионы');
    error.status = res.status;
    throw error;
  }

  const data = await res.json();

  // Normalize: extract translated name for the requested language
  const items = (data.items ?? []).map((sub) => {
    const tr = (sub.translations ?? []).find((t) => t.lang_code === lang);
    return {
      code: sub.code,
      name: tr?.name ?? sub.code,
    };
  });

  return { items, total: data.total ?? items.length };
}
