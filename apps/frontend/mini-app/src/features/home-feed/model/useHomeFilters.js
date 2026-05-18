'use client';

import { useEffect, useMemo, useRef, useState } from 'react';

import { useGetCategoriesQuery, useGetCategoriesWithTypesQuery } from '@/entities/category';
import { useGetBrandsQuery } from '@/entities/brand';

import { normalizeSearchText } from '../lib/utils';

/**
 * Home page filter domain — audit #1: extracted from the `app/page.jsx`
 * god-component (~160 lines). Owns:
 *  • filter value state (category/sort/type/brand/price/delivery/original)
 *  • metadata queries (categories immediately; types/brands lazy, skip-gated)
 *  • all derives: options, chip labels, counts, id→name maps
 *  • `hasActiveFilters` / `showResults` — page-mode computation and skip-gate
 *
 * `commitSearch` / `handleCategoryChange` / `resetToHome` also touch the
 * search state, so they remain in the page as glue. This hook provides them
 * with `setActiveCategoryId` etc. + `categoriesRef`/`brandsRef`
 * (latest list — for exact-match lookup without dep-churn).
 *
 * @param {{ submittedQuery: string, isFiltersOpen: boolean, isTypeOpen: boolean, isBrandOpen: boolean }} params
 */
const DEFAULT_CATEGORY_ID = '019d7712-4563-76ad-984f-18d775fe9b26';

const formatNum = (n) => (n == null ? '' : Number(n).toLocaleString('ru-RU'));

export function useHomeFilters({ submittedQuery, isFiltersOpen, isTypeOpen, isBrandOpen }) {
  // `commitSearch` (page glue) reads from these refs — it gets the latest
  // values without adding `brandsList`/`categories` to the dep array.
  const brandsRef = useRef([]);
  const categoriesRef = useRef([]);

  /* ── Filter state ── */
  const [activeCategoryId, setActiveCategoryId] = useState(null);
  const [sort, setSort] = useState('popular');
  const [typeIds, setTypeIds] = useState([]);
  const [brandIds, setBrandIds] = useState([]);
  const [priceRange, setPriceRange] = useState({ min: null, max: null });
  const [delivery, setDelivery] = useState({ inStock: false, fromChina: false });
  const [original, setOriginal] = useState(false);

  /* ── Categories (loaded early — products need a default category_id) ── */
  const { data: categoriesData } = useGetCategoriesQuery();
  const defaultCategoryId = useMemo(() => {
    if (!Array.isArray(categoriesData) || !categoriesData.length) return DEFAULT_CATEGORY_ID;
    const first = categoriesData[0];
    return first?.id ?? DEFAULT_CATEGORY_ID;
  }, [categoriesData]);

  /* ── Derived mode flags ── */
  const hasActiveFilters =
    activeCategoryId != null ||
    (Array.isArray(typeIds) && typeIds.length > 0) ||
    (Array.isArray(brandIds) && brandIds.length > 0) ||
    priceRange.min != null ||
    priceRange.max != null;
  const showResults = normalizeSearchText(submittedQuery).length > 0 || hasActiveFilters;

  /* ── Filter metadata (lazy — fetched only when the filter UI is active) ──
   * In home mode these lists aren't needed — product cards carry their
   * brand/type info inside the backend response. Cache 30 minutes
   * (keepUnusedDataFor: 1800). */
  const filtersNeedBrands =
    isFiltersOpen || isBrandOpen || (Array.isArray(brandIds) && brandIds.length > 0) || showResults;
  const filtersNeedTypes =
    isFiltersOpen || isTypeOpen || (Array.isArray(typeIds) && typeIds.length > 0) || showResults;

  const { data: categoriesWithTypesData } = useGetCategoriesWithTypesQuery(undefined, {
    skip: !filtersNeedTypes,
  });
  const { data: brandsData } = useGetBrandsQuery(undefined, {
    skip: !filtersNeedBrands,
  });

  /* ── Derived: options / labels / counts ── */
  const categories = useMemo(() => {
    if (!Array.isArray(categoriesData)) return [];
    return categoriesData
      .filter((c) => c && typeof c === 'object')
      .map((c) => ({ id: c.id, name: c.name ?? c.title ?? c.label ?? '' }))
      .filter((c) => c.id != null && String(c.name).trim());
  }, [categoriesData]);
  // Latest-value ref mirror — not during render, via effect (react-hooks/refs).
  // `commitSearch` (page glue) reads it on a user event after commit.
  useEffect(() => {
    categoriesRef.current = categories;
  }, [categories]);

  const typeOptions = useMemo(() => {
    if (!categoriesWithTypesData) return [];
    const items = [];
    const pushCategory = (label, types) => {
      if (!label) return;
      items.push({ kind: 'section', label: String(label).toUpperCase() });
      for (const t of types) {
        if (!t || typeof t !== 'object') continue;
        const id = t.id;
        const name = t.name ?? t.title ?? t.label ?? '';
        if (id == null || !String(name).trim()) continue;
        items.push({ value: id, label: String(name) });
      }
    };
    const root = Array.isArray(categoriesWithTypesData)
      ? categoriesWithTypesData
      : Array.isArray(categoriesWithTypesData?.items)
        ? categoriesWithTypesData.items
        : [];
    for (const c of root) {
      if (!c || typeof c !== 'object') continue;
      pushCategory(c.name ?? c.title ?? c.label ?? '', Array.isArray(c.types) ? c.types : []);
    }
    return items;
  }, [categoriesWithTypesData]);

  const brandsList = useMemo(() => {
    if (!Array.isArray(brandsData)) return [];
    return brandsData
      .filter((b) => b && typeof b === 'object')
      .map((b) => ({ id: b.id, name: b.name ?? b.title ?? b.label ?? '' }))
      .filter((b) => b.id != null && String(b.name).trim());
  }, [brandsData]);
  // Latest-value ref mirror — via effect (see the `categoriesRef` comment above).
  useEffect(() => {
    brandsRef.current = brandsList;
  }, [brandsList]);

  const brandOptions = useMemo(() => {
    return [...brandsList]
      .sort((a, b) => String(a.name).localeCompare(String(b.name)))
      .map((b) => ({ value: b.id, label: b.name }));
  }, [brandsList]);

  const categoryLabel = useMemo(() => {
    if (activeCategoryId == null) return null;
    const hit = categories.find((c) => String(c.id) === String(activeCategoryId));
    return hit?.name ?? String(activeCategoryId);
  }, [categories, activeCategoryId]);

  const categoryChipLabel = activeCategoryId != null ? (categoryLabel ?? 'Категория') : 'Категория';

  const categoryOptions = useMemo(() => {
    return categories.map((c) => ({ value: c.id, label: c.name }));
  }, [categories]);

  const hasDeliveryFilter = delivery.inStock || delivery.fromChina;
  const deliveryChipLabel = useMemo(() => {
    if (delivery.inStock && delivery.fromChina) return 'Из наличия, Из Китая';
    if (delivery.inStock) return 'Из наличия';
    if (delivery.fromChina) return 'Из Китая';
    return 'Доставка';
  }, [delivery]);

  const priceLabel = useMemo(() => {
    const min = priceRange?.min ?? null;
    const max = priceRange?.max ?? null;
    if (min == null && max == null) return 'Цена';
    if (min != null && max != null) return `${formatNum(min)}–${formatNum(max)} ₽`;
    if (min != null) return `От ${formatNum(min)} ₽`;
    return `До ${formatNum(max)} ₽`;
  }, [priceRange]);

  const brandIdToName = useMemo(() => {
    const m = new Map();
    for (const b of brandsList) m.set(String(b.id), String(b.name));
    return m;
  }, [brandsList]);

  const typeIdToName = useMemo(() => {
    const m = new Map();
    for (const it of typeOptions) {
      if (it?.kind === 'section' || it?.value == null) continue;
      m.set(String(it.value), String(it.label ?? it.value));
    }
    return m;
  }, [typeOptions]);

  const brandChipLabel = useMemo(() => {
    if (!brandIds?.length) return 'Бренд';
    const first = brandIdToName.get(String(brandIds[0])) ?? String(brandIds[0]);
    if (brandIds.length === 1) return first;
    return `${first} +${brandIds.length - 1}`;
  }, [brandIdToName, brandIds]);

  const typeChipLabel = useMemo(() => {
    if (!typeIds?.length) return 'Тип';
    const first = typeIdToName.get(String(typeIds[0])) ?? String(typeIds[0]);
    if (typeIds.length === 1) return first;
    return `${first} +${typeIds.length - 1}`;
  }, [typeIdToName, typeIds]);

  const activeFilterCount = useMemo(() => {
    let count = 0;
    if (activeCategoryId != null) count++;
    if (typeIds.length > 0) count++;
    if (brandIds.length > 0) count++;
    if (priceRange.min != null || priceRange.max != null) count++;
    if (delivery.inStock) count++;
    if (delivery.fromChina) count++;
    if (original) count++;
    return count;
  }, [activeCategoryId, typeIds, brandIds, priceRange, delivery, original]);

  const filterCategories = useMemo(() => {
    return categories.map((c) => ({ id: c.id, name: c.name }));
  }, [categories]);

  return {
    // state + setters
    activeCategoryId,
    setActiveCategoryId,
    sort,
    setSort,
    typeIds,
    setTypeIds,
    brandIds,
    setBrandIds,
    priceRange,
    setPriceRange,
    delivery,
    setDelivery,
    original,
    setOriginal,
    // metadata
    defaultCategoryId,
    categories,
    typeOptions,
    brandOptions,
    categoryOptions,
    filterCategories,
    // chip labels / counts
    categoryChipLabel,
    typeChipLabel,
    brandChipLabel,
    priceLabel,
    deliveryChipLabel,
    hasDeliveryFilter,
    activeFilterCount,
    // id → name maps (FiltersSheet value translation)
    brandIdToName,
    typeIdToName,
    // derived mode flags
    hasActiveFilters,
    showResults,
    // latest-value refs for commitSearch glue
    categoriesRef,
    brandsRef,
  };
}
