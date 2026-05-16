'use client';

import { useEffect, useMemo, useState } from 'react';

/**
 * Manzil suggest (geo subdivision) — query 250ms debounce, AbortController
 * cancel. Audit #1: `app/checkout/pickup/page.jsx`'dan ajratildi. Fully
 * self-contained — hech qanday input shart emas.
 *
 * BFF route: `POST /api/geo/suggest/address` — backend'imizning geo katalog'iga
 * proxy (DaData shape'da response saqlanadi).
 *
 * @returns {{
 *   query: string,
 *   setQuery: (v: string) => void,
 *   suggestions: any[],
 *   setSuggestions: (v: any[]) => void,
 *   items: { id: string, title: string, subtitle: string, lat: number|null, lon: number|null }[],
 * }}
 */
export function useAddressSuggest() {
  const [query, setQuery] = useState('');
  const [suggestions, setSuggestions] = useState([]);

  useEffect(() => {
    const q = query.trim();
    if (!q) {
      setSuggestions([]);
      return;
    }

    const ctrl = new AbortController();

    const t = window.setTimeout(async () => {
      try {
        const res = await fetch('/api/geo/suggest/address', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ query: q, count: 10 }),
          signal: ctrl.signal,
        });

        if (!res.ok) {
          setSuggestions([]);
          return;
        }

        const data = await res.json();
        const s = data?.suggestions;
        setSuggestions(Array.isArray(s) ? s : []);
      } catch {
        if (ctrl.signal.aborted) return;
        setSuggestions([]);
      }
    }, 250);

    return () => {
      window.clearTimeout(t);
      ctrl.abort();
    };
  }, [query]);

  const items = useMemo(() => {
    if (!query.trim()) return [];
    if (suggestions.length === 0) return [];

    return suggestions.map((x, index) => {
      const d = x.data;
      const subtitle =
        d?.city_with_type || d?.settlement_with_type || d?.area_with_type || d?.country || '';

      const latRaw = d?.geo_lat ?? null;
      const lonRaw = d?.geo_lon ?? null;
      const lat = latRaw == null ? null : Number(latRaw);
      const lon = lonRaw == null ? null : Number(lonRaw);

      return {
        id: `geo-${d?.subdivision_code || index}`,
        title: x.value || query,
        subtitle,
        lat: Number.isFinite(lat) ? lat : null,
        lon: Number.isFinite(lon) ? lon : null,
      };
    });
  }, [query, suggestions]);

  return { query, setQuery, suggestions, setSuggestions, items };
}
