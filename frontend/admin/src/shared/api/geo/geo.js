import { apiClient } from '@/shared/api/client-fetch';

const DEFAULT_COUNTRY_LIMIT = 300;
// Subdivisions: large enough to fit even Russia (85+) without truncation
// while still being a single, fast request that we can filter client-side.
const DEFAULT_SUBDIVISION_LIMIT = 500;

function pickTranslatedName(translations, lang, fallback) {
  const tr = (translations ?? []).find((t) => t.lang_code === lang);
  return tr?.name ?? fallback;
}

export async function fetchCountries({
  lang = 'ru',
  limit = DEFAULT_COUNTRY_LIMIT,
} = {}) {
  const qs = new URLSearchParams({ lang, limit: String(limit) });
  const data = await apiClient.get(`/api/geo/countries?${qs}`);

  const items = (data.items ?? [])
    .map((c) => ({
      code: c.alpha2,
      name: pickTranslatedName(c.translations, lang, c.alpha2),
    }))
    .sort((a, b) => a.name.localeCompare(b.name, 'ru'));

  return { items, total: data.total ?? items.length };
}

export async function fetchSubdivisions(
  countryCode,
  { lang = 'ru', search = '', limit = DEFAULT_SUBDIVISION_LIMIT } = {},
) {
  const qs = new URLSearchParams({ lang, limit: String(limit) });
  if (search) qs.set('search', search);

  try {
    const data = await apiClient.get(
      `/api/geo/subdivisions/${encodeURIComponent(countryCode)}?${qs}`,
    );
    const items = (data.items ?? []).map((sub) => ({
      code: sub.code,
      name: pickTranslatedName(sub.translations, lang, sub.code),
    }));
    return { items, total: data.total ?? items.length };
  } catch (err) {
    if (err?.status === 404) {
      return { items: [], total: 0, notFound: true };
    }
    throw err;
  }
}
