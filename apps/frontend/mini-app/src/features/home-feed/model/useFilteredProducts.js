'use client';

import { useEffect, useMemo, useState } from 'react';

import { mapProductCard } from '@/entities/product';

import { normalizeSearchText, priceToNumber } from '../lib/utils';

/**
 * Home page filter/search results — fetches several pages by cursor (max 3)
 * from `/storefront/{search,products}` and collects up to 30 results.
 * Audit #1: extracted from the `app/page.jsx` god-component (~115 lines).
 *
 * `filterKey` — JSON serialization of all filter arguments; if null
 * (no filter/search) no request is sent. `priceBounds` — min/max price
 * from the loaded results (for PriceSheet placeholders).
 *
 * @param {{
 *   submittedQuery: string, activeCategoryId: string|null,
 *   typeIds: string[], brandIds: string[],
 *   priceRange: { min: number|null, max: number|null },
 *   sort: string, defaultCategoryId: string,
 * }} params
 */
export function useFilteredProducts({
  submittedQuery,
  activeCategoryId,
  typeIds,
  brandIds,
  priceRange,
  sort,
  defaultCategoryId,
}) {
  const [filteredRaw, setFilteredRaw] = useState([]);
  const [isFilteredLoading, setIsFilteredLoading] = useState(false);

  const filterKey = useMemo(() => {
    const q = normalizeSearchText(submittedQuery);
    const cId = activeCategoryId;
    const tId = Array.isArray(typeIds) && typeIds.length ? typeIds[0] : null;
    const bId = Array.isArray(brandIds) && brandIds.length ? brandIds[0] : null;
    const pMin = priceRange?.min ?? null;
    const pMax = priceRange?.max ?? null;
    if (!q && cId == null && tId == null && bId == null && pMin == null && pMax == null)
      return null;
    return JSON.stringify({
      q,
      categoryId: cId,
      typeId: tId,
      brandId: bId,
      priceMin: pMin,
      priceMax: pMax,
    });
  }, [activeCategoryId, brandIds, priceRange, submittedQuery, typeIds]);

  useEffect(() => {
    if (!filterKey) {
      setFilteredRaw([]);
      setIsFilteredLoading(false);
      return;
    }

    const parsed = JSON.parse(filterKey);
    const q = String(parsed.q || '');
    let cancelled = false;
    const controller = new AbortController();

    const run = async () => {
      setIsFilteredLoading(true);
      const matches = [];
      const limit = 30;
      let cursor = undefined;
      const maxPages = 3;
      const need = 30;

      try {
        for (let page = 0; page < maxPages; page++) {
          if (cancelled) return;
          const sp = new URLSearchParams();
          sp.set('limit', String(limit));
          if (cursor) sp.set('cursor', cursor);
          // categoryId is required for storefront/products — use filter value or default.
          // Backend storefront query params are camelCase (see openapi.json).
          const catId = parsed.categoryId ?? defaultCategoryId;
          if (catId != null) sp.set('categoryId', String(catId));
          if (parsed.brandId != null) sp.set('brandId', String(parsed.brandId));
          if (parsed.priceMin != null) sp.set('priceMin', String(parsed.priceMin));
          if (parsed.priceMax != null) sp.set('priceMax', String(parsed.priceMax));
          if (sort && sort !== 'popular') sp.set('sort', sort);

          // The backend storefront routers are mounted under `/storefront/*`
          // (the `catalog` module, but without `catalog` in the URL prefix).
          const endpoint = q
            ? `/api/backend/api/v1/storefront/search?q=${encodeURIComponent(q)}&${sp.toString()}`
            : `/api/backend/api/v1/storefront/products?${sp.toString()}`;

          const res = await fetch(endpoint, {
            method: 'GET',
            credentials: 'include',
            signal: controller.signal,
            headers: { accept: 'application/json' },
          });
          if (!res.ok) break;

          const json = await res.json();
          const items = Array.isArray(json?.items) ? json.items : Array.isArray(json) ? json : [];
          const mapped = items.map((p) => mapProductCard(p, null)).filter(Boolean);

          for (const p of mapped) {
            matches.push(p);
            if (matches.length >= need) break;
          }
          if (matches.length >= need) break;
          if (!json?.hasNext) break;
          cursor = json?.nextCursor;
          if (!cursor) break;
        }
      } catch {
        // ignore
      } finally {
        if (!cancelled) {
          setFilteredRaw(matches.slice(0, 30));
          setIsFilteredLoading(false);
        }
      }
    };

    run();
    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [filterKey, sort, defaultCategoryId]);

  const filteredProducts = useMemo(() => {
    const q = normalizeSearchText(submittedQuery);
    const base = q
      ? filteredRaw.filter((p) =>
          normalizeSearchText(`${p?.name ?? ''} ${p?.brand ?? ''}`).includes(q)
        )
      : filteredRaw;

    if (sort === 'price_asc')
      return base.sort((a, b) => priceToNumber(a.price) - priceToNumber(b.price));
    if (sort === 'price_desc')
      return base.sort((a, b) => priceToNumber(b.price) - priceToNumber(a.price));
    return base;
  }, [filteredRaw, sort, submittedQuery]);

  // Price bounds from the loaded results — for PriceSheet/FiltersSheet
  // placeholders.
  const priceBounds = useMemo(() => {
    let min = null;
    let max = null;
    for (const p of filteredProducts) {
      const price = priceToNumber(p.price);
      if (!price) continue;
      if (min == null || price < min) min = price;
      if (max == null || price > max) max = price;
    }
    return { min, max };
  }, [filteredProducts]);

  return { filteredProducts, isFilteredLoading, priceBounds };
}
