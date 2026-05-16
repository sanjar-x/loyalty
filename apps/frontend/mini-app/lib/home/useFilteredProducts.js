'use client';

import { useEffect, useMemo, useState } from 'react';

import { mapProductCard } from '@/lib/adapters/mapProductCard';

import { normalizeSearchText, priceToNumber } from './utils';

/**
 * Bosh sahifa filtr/qidiruv natijalari — `/storefront/{search,products}` ga
 * cursor bo'yicha bir necha sahifa (maks 3) yuklab, 30 tagacha natija yig'adi.
 * Audit #1: `app/page.jsx` god-komponentidan ajratildi (~115 satr).
 *
 * `filterKey` — barcha filtr argumentlarining JSON serializatsiyasi; null
 * bo'lsa (hech qanday filtr/qidiruv yo'q) so'rov yuborilmaydi. `priceBounds`
 * — yuklangan natijalardan min/max narx (PriceSheet placeholder'lari uchun).
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
          // Backend storefront query params are camelCase (см. openapi.json).
          const catId = parsed.categoryId ?? defaultCategoryId;
          if (catId != null) sp.set('categoryId', String(catId));
          if (parsed.brandId != null) sp.set('brandId', String(parsed.brandId));
          if (parsed.priceMin != null) sp.set('priceMin', String(parsed.priceMin));
          if (parsed.priceMax != null) sp.set('priceMax', String(parsed.priceMax));
          if (sort && sort !== 'popular') sp.set('sort', sort);

          // Storefront роутеры бэкенда смонтированы под `/storefront/*`
          // (модуль `catalog`, но без `catalog` в URL-префиксе).
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

  // Yuklangan natijalardan narx chegaralari — PriceSheet/FiltersSheet
  // placeholder'lari uchun.
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
