'use client';

import { useQuery } from '@tanstack/react-query';
import { SESSION_STATIC_STALE_TIME_MS } from '@/shared/query';
import { fetchCountries, fetchSubdivisions } from './geo';
import { geoKeys } from './keys';

/**
 * ISO 3166-1 country list — practically immutable per session.
 * 30-min staleTime to avoid any refetch noise during long admin sessions.
 */
export function useCountries({ lang = 'ru', limit } = {}) {
  return useQuery({
    queryKey: geoKeys.countries({ lang, limit }),
    queryFn: () => fetchCountries({ lang, limit }),
    staleTime: SESSION_STATIC_STALE_TIME_MS,
  });
}

/**
 * Country subdivisions — depends on the parent country code; cached per code
 * for 30 minutes. Disabled until a country code is known.
 */
export function useSubdivisions(countryCode, { lang = 'ru' } = {}) {
  return useQuery({
    queryKey: geoKeys.subdivisions({ countryCode, lang }),
    queryFn: () => fetchSubdivisions(countryCode, { lang }),
    staleTime: SESSION_STATIC_STALE_TIME_MS,
    enabled: Boolean(countryCode),
  });
}
