"use client";
import {
  Suspense,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import {
  useGetTrendingProductsQuery,
  useGetForYouFeedQuery,
  useLazyGetForYouFeedQuery,
  useGetCategoriesQuery,
  useGetCategoriesWithTypesQuery,
  useGetBrandsQuery,
  useCreateSearchHistoryMutation,
} from "@/lib/store/api";

import { useSearchParams, useRouter } from "next/navigation";
import SearchBar from "@/components/blocks/search/SearchBar";
import SearchOverlay from "@/components/blocks/search/SearchOverlay";
import Header from "@/components/layout/Header";
import Footer from "@/components/layout/Footer";
import CategoryTabs from "@/components/blocks/home/CategoryTabs";
import FriendsSection from "@/components/blocks/home/FriendsSection";
import HomeDeliveryStatusCard from "@/components/blocks/home/HomeDeliveryStatusCard";
import ProductSection from "@/components/blocks/product/ProductSection";
import SelectSheet from "@/components/blocks/search/SelectSheet";
import PriceSheet from "@/components/blocks/search/PriceSheet";
import FiltersSheet from "@/components/blocks/search/FiltersSheet";
import { cn } from "@/lib/format/cn";

import { useItemFavorites } from "@/lib/hooks/useItemFavorites";

import styles from "./page.module.css";

import { mapProductCard } from "@/lib/format/mapProductCard";

/* ── Helpers ── */

function normalize(value) {
  return String(value || "")
    .trim()
    .replace(/\s+/g, " ")
    .toLowerCase();
}

// Mapper'lar olib tashlandi — `lib/format/mapProductCard.js` orqali umumiy
// `mapProductCard()` ishlatiladi (`formatRubPrice`, `getProductPhotoCandidates`,
// `getProductGallery` shu modul ichida).

function priceToNumber(value) {
  const n = Number(String(value || "").replace(/[^0-9]/g, ""));
  return Number.isFinite(n) ? n : 0;
}

/* ── Component ── */

export default function HomePage() {
  return (
    <Suspense>
      <Home />
    </Suspense>
  );
}

function Home() {
  const { favoriteItemIds, toggleFavorite } = useItemFavorites("product");
  const searchParams = useSearchParams();
  const router = useRouter();
  const inputRef = useRef(null);
  const blurCloseTimerRef = useRef(null);
  const sentinelRef = useRef(null);
  const reopenFiltersAfterPickerRef = useRef(false);
  const initializedFromUrl = useRef(false);
  const brandsRef = useRef([]);
  const categoriesRef = useRef([]);
  const cameFromExternalSearch = useRef(false);
  const lastScrollY = useRef(0);
  const [filtersBarHidden, setFiltersBarHidden] = useState(false);

  /* ── Categories (loaded early — products need a default category_id) ── */
  const { data: categoriesData } = useGetCategoriesQuery();
  const DEFAULT_CATEGORY_ID = "019d7712-4563-76ad-984f-18d775fe9b26";
  const defaultCategoryId = useMemo(() => {
    if (!Array.isArray(categoriesData) || !categoriesData.length) return DEFAULT_CATEGORY_ID;
    const first = categoriesData[0];
    return first?.id ?? DEFAULT_CATEGORY_ID;
  }, [categoriesData]);

  /* ── Search state ── */
  const [query, setQuery] = useState("");
  const [submittedQuery, setSubmittedQuery] = useState("");
  const [isFocused, setIsFocused] = useState(false);
  const [hasTyped, setHasTyped] = useState(false);
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const [isSearchActivated, setSearchActivated] = useState(false);

  /* ── Filter state ── */
  const [activeCategoryId, setActiveCategoryId] = useState(null);
  const [sort, setSort] = useState("popular");
  const [typeIds, setTypeIds] = useState([]);
  const [brandIds, setBrandIds] = useState([]);
  const [priceRange, setPriceRange] = useState({ min: null, max: null });
  const [delivery, setDelivery] = useState({ inStock: false, fromChina: false });
  const [original, setOriginal] = useState(false);

  /* ── Sheet open state ── */
  const [sortOpen, setSortOpen] = useState(false);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [typeOpen, setTypeOpen] = useState(false);
  const [brandOpen, setBrandOpen] = useState(false);
  const [priceOpen, setPriceOpen] = useState(false);
  const [categoryOpen, setCategoryOpen] = useState(false);
  const [deliveryOpen, setDeliveryOpen] = useState(false);

  /* ── Derived mode ── */
  const showSuggestions = isFocused && hasTyped && normalize(query).length > 0;
  const showOverlay = isFocused;
  const hasActiveFilters =
    activeCategoryId != null ||
    (Array.isArray(typeIds) && typeIds.length > 0) ||
    (Array.isArray(brandIds) && brandIds.length > 0) ||
    priceRange.min != null ||
    priceRange.max != null;
  const showResults = normalize(submittedQuery).length > 0 || hasActiveFilters;
  const isHomeMode = !showResults && !showOverlay;

  /* ── Reset to home ── */
  const resetToHome = useCallback(() => {
    setQuery("");
    setSubmittedQuery("");
    setIsFocused(false);
    setHasTyped(false);
    setSearchActivated(false);
    setActiveCategoryId(null);
    setTypeIds([]);
    setBrandIds([]);
    setPriceRange({ min: null, max: null });
    setDelivery({ inStock: false, fromChina: false });
    setOriginal(false);
    setSort("popular");
    inputRef.current?.blur?.();
  }, []);

  /* ── Initialize filters from URL params (e.g. from catalog page) ── */
  useEffect(() => {
    if (initializedFromUrl.current) return;
    initializedFromUrl.current = true;

    const categoryId = searchParams.get("category_id");
    const typeId = searchParams.get("type_id");
    const brandId = searchParams.get("brand_id");
    const q = searchParams.get("query");

    const openSearch = searchParams.get("search");

    if (!categoryId && !typeId && !brandId && !q && !openSearch) return;

    if (categoryId) setActiveCategoryId(categoryId);
    if (typeId) setTypeIds([typeId]);
    if (brandId) setBrandIds([brandId]);
    if (q) {
      setQuery(q);
      setSubmittedQuery(q);
      setSearchActivated(true);
    }
    if (openSearch) {
      cameFromExternalSearch.current = true;
      setIsFocused(true);
      setSearchActivated(true);
      setTimeout(() => inputRef.current?.focus?.(), 100);
    }

    // Clean URL without reloading
    if (window.history.replaceState) {
      window.history.replaceState({}, "", "/");
    }
  }, [searchParams]);

  /* Expose back handler for Telegram BackButton & Header */
  const handleBack = useCallback(() => {
    // 1. If any sheet is open → close it
    if (filtersOpen) { setFiltersOpen(false); return; }
    if (sortOpen) { setSortOpen(false); return; }
    if (typeOpen) { setTypeOpen(false); return; }
    if (brandOpen) { setBrandOpen(false); return; }
    if (priceOpen) { setPriceOpen(false); return; }
    if (categoryOpen) { setCategoryOpen(false); return; }
    if (deliveryOpen) { setDeliveryOpen(false); return; }
    // 2. If came from external page (e.g. catalog) → go back in history
    if (cameFromExternalSearch.current) {
      cameFromExternalSearch.current = false;
      router.back();
      return;
    }
    // 3. If search/filters active → go home
    resetToHome();
  }, [filtersOpen, sortOpen, typeOpen, brandOpen, priceOpen, categoryOpen, deliveryOpen, resetToHome, router]);

  useEffect(() => {
    if (!isHomeMode || filtersOpen || sortOpen || typeOpen || brandOpen || priceOpen || categoryOpen || deliveryOpen) {
      window.__LM_HOME_BACK__ = handleBack;
    } else {
      window.__LM_HOME_BACK__ = null;
    }
    return () => {
      window.__LM_HOME_BACK__ = null;
    };
  }, [isHomeMode, handleBack, filtersOpen, sortOpen, typeOpen, brandOpen, priceOpen, categoryOpen, deliveryOpen]);

  /* ── Hide filtersBar on scroll down, show on scroll up ── */
  useEffect(() => {
    let ticking = false;
    const THRESHOLD = 10;

    const onScroll = () => {
      if (ticking) return;
      ticking = true;
      requestAnimationFrame(() => {
        const y = window.scrollY;
        const delta = y - lastScrollY.current;
        if (delta > THRESHOLD && y > 80) {
          setFiltersBarHidden(true);
        } else if (delta < -THRESHOLD) {
          setFiltersBarHidden(false);
        }
        lastScrollY.current = y;
        ticking = false;
      });
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  /* ── Search debounce ── */
  useEffect(() => {
    if (!showSuggestions) {
      setDebouncedQuery("");
      return;
    }
    const next = String(query || "");
    const t = window.setTimeout(() => setDebouncedQuery(next), 220);
    return () => window.clearTimeout(t);
  }, [query, showSuggestions]);

  /* ── Search history mutation ── */
  const [createSearchHistory] = useCreateSearchHistoryMutation();

  const commitSearch = useCallback(
    (value) => {
      const next = String(value || "").trim();
      if (!next) return;
      if (blurCloseTimerRef.current) {
        window.clearTimeout(blurCloseTimerRef.current);
        blurCloseTimerRef.current = null;
      }
      setIsFocused(false);
      setHasTyped(false);
      setQuery(next);
      setSubmittedQuery(next);

      /* Auto-apply filters when query matches a brand or category name */
      const nq = normalize(next);
      const matchedBrand = brandsRef.current.find((b) => normalize(b.name) === nq);
      if (matchedBrand) setBrandIds([matchedBrand.id]);
      const matchedCategory = categoriesRef.current.find((c) => normalize(c.name) === nq);
      if (matchedCategory) setActiveCategoryId(matchedCategory.id);

      inputRef.current?.blur?.();
      try {
        createSearchHistory({
          query: next,
          parameters: {
            sort,
            category_id: activeCategoryId,
            type_ids: Array.isArray(typeIds) ? typeIds : [],
            brand_ids: Array.isArray(brandIds) ? brandIds : [],
            price_min: priceRange?.min ?? null,
            price_max: priceRange?.max ?? null,
            delivery,
            original,
          },
        });
      } catch {
        // ignore
      }
    },
    [
      activeCategoryId,
      brandIds,
      createSearchHistory,
      delivery,
      original,
      priceRange,
      sort,
      typeIds,
    ],
  );

  /* ── Category tab change ── */
  const handleCategoryChange = useCallback((categoryId) => {
    setActiveCategoryId(categoryId);
    // Reset sub-filters when switching category
    setTypeIds([]);
    setBrandIds([]);
    setPriceRange({ min: null, max: null });
    setDelivery({ inStock: false, fromChina: false });
    setOriginal(false);
    setSort("popular");
    // Clear search when going back to "Для вас"
    if (categoryId == null) {
      setSubmittedQuery("");
      setQuery("");
    }
  }, []);

  /* ── Home: trending ("Только что купили" placeholder) ── */
  const {
    data: latestData,
    isLoading: isLatestLoading,
    isFetching: isLatestFetching,
  } = useGetTrendingProductsQuery({ limit: 10, window: "weekly" });

  const isLatestInitialLoading =
    Boolean(isLatestLoading || isLatestFetching) &&
    (!Array.isArray(latestData) || latestData.length === 0);

  /* ── Home: personalized "Для вас" feed (cursor pagination) ── */
  const PAGE_SIZE = 10;
  const {
    data: initialProductsResponse,
    isLoading: isInitialProductsLoading,
    isFetching: isInitialProductsFetching,
  } = useGetForYouFeedQuery({ limit: PAGE_SIZE });

  const initialProductsItems = useMemo(() => {
    if (!initialProductsResponse) return [];
    return Array.isArray(initialProductsResponse.items) ? initialProductsResponse.items : [];
  }, [initialProductsResponse]);

  const [extraRecommendedRaw, setExtraRecommendedRaw] = useState([]);
  const [recommendedHasMore, setRecommendedHasMore] = useState(true);
  const [loadMoreError, setLoadMoreError] = useState(null);
  const retryAttemptsRef = useRef(0);
  const retryTimerRef = useRef(null);
  const [nextCursorRef] = useState(() => ({ current: null }));
  const [triggerGetForYou, forYouQuery] = useLazyGetForYouFeedQuery();

  // Sync initial response cursor
  useEffect(() => {
    if (initialProductsResponse?.nextCursor) {
      nextCursorRef.current = initialProductsResponse.nextCursor;
    }
    if (initialProductsResponse && !initialProductsResponse.hasNext) {
      setRecommendedHasMore(false);
    }
  }, [initialProductsResponse, nextCursorRef]);

  // Cancel any pending retry on unmount
  useEffect(() => {
    return () => {
      if (retryTimerRef.current) {
        clearTimeout(retryTimerRef.current);
        retryTimerRef.current = null;
      }
    };
  }, []);

  const mergeUniqueById = useCallback((prev, next) => {
    const out = Array.isArray(prev) ? [...prev] : [];
    const seen = new Set(
      out.map((p) => p?.id).filter((id) => id != null),
    );
    const rows = Array.isArray(next) ? next : [];
    for (const p of rows) {
      if (p?.id == null || seen.has(p.id)) continue;
      seen.add(p.id);
      out.push(p);
    }
    return out;
  }, []);

  const MAX_AUTO_RETRIES = 3;
  const loadMoreRecommended = useCallback(async () => {
    if (!initialProductsItems.length) return;
    if (!recommendedHasMore) return;
    if (forYouQuery.isFetching) return;
    const cursor = nextCursorRef.current;
    if (!cursor) {
      setRecommendedHasMore(false);
      return;
    }
    try {
      const response = await triggerGetForYou({
        cursor,
        limit: PAGE_SIZE,
      }).unwrap();
      const arr = Array.isArray(response?.items) ? response.items : [];
      setExtraRecommendedRaw((prev) => mergeUniqueById(prev, arr));
      if (response?.nextCursor) {
        nextCursorRef.current = response.nextCursor;
      } else {
        nextCursorRef.current = null;
      }
      setRecommendedHasMore(Boolean(response?.hasNext));
      setLoadMoreError(null);
      retryAttemptsRef.current = 0;
    } catch (err) {
      // RTK Query errors: { status, data } — status may be a number (HTTP),
      // "FETCH_ERROR" (network), "TIMEOUT_ERROR", or "PARSING_ERROR".
      const status = err?.status;
      const isHttpStatus = typeof status === "number";
      const isTransient =
        !isHttpStatus /* network / timeout / parsing */ ||
        (status >= 500 && status <= 599) ||
        status === 408 ||
        status === 429;

      if (isTransient && retryAttemptsRef.current < MAX_AUTO_RETRIES) {
        const attempt = retryAttemptsRef.current + 1;
        retryAttemptsRef.current = attempt;
        // Exponential backoff: 1s → 2s → 4s (with ±20% jitter)
        const base = 1000 * Math.pow(2, attempt - 1);
        const jitter = base * (0.8 + Math.random() * 0.4);
        const delay = Math.round(jitter);
        if (retryTimerRef.current) clearTimeout(retryTimerRef.current);
        retryTimerRef.current = setTimeout(() => {
          retryTimerRef.current = null;
          // Re-trigger: cursor is unchanged (wasn't advanced on failure)
          loadMoreRecommended();
        }, delay);
        setLoadMoreError({ transient: true, attempt });
        return;
      }

      // Auto-retries exhausted OR non-transient (4xx except 408/429):
      // surface error UI, keep cursor intact so user can manually retry.
      setLoadMoreError({
        transient: isTransient,
        attempt: retryAttemptsRef.current,
        exhausted: true,
      });
    }
  }, [
    initialProductsItems,
    mergeUniqueById,
    forYouQuery.isFetching,
    recommendedHasMore,
    triggerGetForYou,
    nextCursorRef,
  ]);

  const retryLoadMore = useCallback(() => {
    retryAttemptsRef.current = 0;
    setLoadMoreError(null);
    loadMoreRecommended();
  }, [loadMoreRecommended]);

  useEffect(() => {
    if (!isHomeMode) return;
    const el = sentinelRef.current;
    if (!el) return;
    if (!initialProductsItems.length) return;
    if (!recommendedHasMore) return;
    // Don't re-trigger while an error is surfaced — user must click "Повторить"
    // (or the auto-retry timer will call loadMoreRecommended directly).
    if (loadMoreError?.exhausted) return;

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0]?.isIntersecting) loadMoreRecommended();
      },
      { root: null, rootMargin: "200px", threshold: 0.01 },
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, [
    initialProductsItems,
    isHomeMode,
    loadMoreRecommended,
    recommendedHasMore,
    loadMoreError?.exhausted,
  ]);

  // Storefront card javoblarida `image` maydoni avtoritetli (StorefrontProductCardResponse).
  // Agar null bo'lsa — backend uchun rasm yo'q, ProductCard `placeholder-product.svg` ko'rsatadi.
  // Shu sababli per-product detail fetch (eski N+1) butunlay olib tashlandi.

  const recentProducts = useMemo(() => {
    const rows = Array.isArray(latestData) ? latestData : [];
    return rows.map((p) => mapProductCard(p, null)).filter(Boolean);
  }, [latestData]);

  const recommendedProducts = useMemo(() => {
    const extraArr = Array.isArray(extraRecommendedRaw) ? extraRecommendedRaw : [];
    const merged = mergeUniqueById(initialProductsItems, extraArr);
    return merged.map((p) => mapProductCard(p, null)).filter(Boolean);
  }, [extraRecommendedRaw, initialProductsItems, mergeUniqueById]);

  const isRecommendedInitialLoading =
    (isInitialProductsLoading || isInitialProductsFetching) &&
    initialProductsItems.length === 0;

  const isRecommendedLoadingMore =
    forYouQuery.isFetching && initialProductsItems.length > 0;
  const isRecommendedRetryPending =
    !!loadMoreError &&
    !loadMoreError.exhausted &&
    loadMoreError.transient &&
    !forYouQuery.isFetching;

  /* ── Filtered results (category/search mode) ── */
  const [filteredRaw, setFilteredRaw] = useState([]);
  const [isFilteredLoading, setIsFilteredLoading] = useState(false);

  const filterKey = useMemo(() => {
    const q = normalize(submittedQuery);
    const cId = activeCategoryId;
    const tId = Array.isArray(typeIds) && typeIds.length ? typeIds[0] : null;
    const bId = Array.isArray(brandIds) && brandIds.length ? brandIds[0] : null;
    const pMin = priceRange?.min ?? null;
    const pMax = priceRange?.max ?? null;
    if (!q && cId == null && tId == null && bId == null && pMin == null && pMax == null)
      return null;
    return JSON.stringify({ q, categoryId: cId, typeId: tId, brandId: bId, priceMin: pMin, priceMax: pMax });
  }, [activeCategoryId, brandIds, priceRange, submittedQuery, typeIds]);

  useEffect(() => {
    if (!filterKey) {
      setFilteredRaw([]);
      setIsFilteredLoading(false);
      return;
    }

    const parsed = JSON.parse(filterKey);
    const q = String(parsed.q || "");
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
          sp.set("limit", String(limit));
          if (cursor) sp.set("cursor", cursor);
          // category_id is required for storefront/products — use filter value or default
          const catId = parsed.categoryId ?? defaultCategoryId;
          if (catId != null) sp.set("category_id", String(catId));
          if (parsed.brandId != null) sp.set("brand_id", String(parsed.brandId));
          if (parsed.priceMin != null) sp.set("price_min", String(parsed.priceMin));
          if (parsed.priceMax != null) sp.set("price_max", String(parsed.priceMax));
          if (sort && sort !== "popular") sp.set("sort", sort);

          const endpoint = q
            ? `/api/backend/api/v1/catalog/storefront/search?q=${encodeURIComponent(q)}&${sp.toString()}`
            : `/api/backend/api/v1/catalog/storefront/products?${sp.toString()}`;

          const res = await fetch(endpoint, {
            method: "GET",
            credentials: "include",
            signal: controller.signal,
            headers: { accept: "application/json" },
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
    const q = normalize(submittedQuery);
    const base = q
      ? filteredRaw.filter((p) => normalize(`${p?.name ?? ""} ${p?.brand ?? ""}`).includes(q))
      : filteredRaw;

    if (sort === "price_asc") return base.sort((a, b) => priceToNumber(a.price) - priceToNumber(b.price));
    if (sort === "price_desc") return base.sort((a, b) => priceToNumber(b.price) - priceToNumber(a.price));
    return base;
  }, [filteredRaw, sort, submittedQuery]);

  /* ── Filter metadata (lazy — faqat filter UI aktiv bo'lganda fetch) ── */
  // Home mode'da (qidiruv/filter yo'q) bu ro'yxatlar kerak emas — product card'lar
  // brand/type ma'lumotini backend javobi ichida olib keladi. Shuning uchun
  // brands/types faqat user filter sheet'larini ochganida yoki filter aktiv
  // bo'lganida yuklanadi. Cache 30 daqiqa ushlab turadi (keepUnusedDataFor: 1800).
  const filtersNeedBrands =
    filtersOpen ||
    brandOpen ||
    (Array.isArray(brandIds) && brandIds.length > 0) ||
    showResults;
  const filtersNeedTypes =
    filtersOpen ||
    typeOpen ||
    (Array.isArray(typeIds) && typeIds.length > 0) ||
    showResults;

  const { data: categoriesWithTypesData } = useGetCategoriesWithTypesQuery(
    undefined,
    { skip: !filtersNeedTypes },
  );
  const { data: brandsData } = useGetBrandsQuery(undefined, {
    skip: !filtersNeedBrands,
  });

  const categories = useMemo(() => {
    if (!Array.isArray(categoriesData)) return [];
    return categoriesData
      .filter((c) => c && typeof c === "object")
      .map((c) => ({ id: c.id, name: c.name ?? c.title ?? c.label ?? "" }))
      .filter((c) => c.id != null && String(c.name).trim());
  }, [categoriesData]);
  categoriesRef.current = categories;

  const typeOptions = useMemo(() => {
    if (!categoriesWithTypesData) return [];
    const items = [];
    const pushCategory = (label, types) => {
      if (!label) return;
      items.push({ kind: "section", label: String(label).toUpperCase() });
      for (const t of types) {
        if (!t || typeof t !== "object") continue;
        const id = t.id;
        const name = t.name ?? t.title ?? t.label ?? "";
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
      if (!c || typeof c !== "object") continue;
      pushCategory(c.name ?? c.title ?? c.label ?? "", Array.isArray(c.types) ? c.types : []);
    }
    return items;
  }, [categoriesWithTypesData]);

  const brandsList = useMemo(() => {
    if (!Array.isArray(brandsData)) return [];
    return brandsData
      .filter((b) => b && typeof b === "object")
      .map((b) => ({ id: b.id, name: b.name ?? b.title ?? b.label ?? "" }))
      .filter((b) => b.id != null && String(b.name).trim());
  }, [brandsData]);
  brandsRef.current = brandsList;

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

  const categoryChipLabel = activeCategoryId != null ? (categoryLabel ?? "Категория") : "Категория";

  const categoryOptions = useMemo(() => {
    return categories.map((c) => ({ value: c.id, label: c.name }));
  }, [categories]);

  const hasDeliveryFilter = delivery.inStock || delivery.fromChina;
  const deliveryChipLabel = useMemo(() => {
    if (delivery.inStock && delivery.fromChina) return "Из наличия, Из Китая";
    if (delivery.inStock) return "Из наличия";
    if (delivery.fromChina) return "Из Китая";
    return "Доставка";
  }, [delivery]);

  const formatNum = (n) => (n == null ? "" : Number(n).toLocaleString("ru-RU"));

  const priceLabel = useMemo(() => {
    const min = priceRange?.min ?? null;
    const max = priceRange?.max ?? null;
    if (min == null && max == null) return "Цена";
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
      if (it?.kind === "section" || it?.value == null) continue;
      m.set(String(it.value), String(it.label ?? it.value));
    }
    return m;
  }, [typeOptions]);

  const brandChipLabel = useMemo(() => {
    if (!brandIds?.length) return "Бренд";
    const first = brandIdToName.get(String(brandIds[0])) ?? String(brandIds[0]);
    if (brandIds.length === 1) return first;
    return `${first} +${brandIds.length - 1}`;
  }, [brandIdToName, brandIds]);

  const typeChipLabel = useMemo(() => {
    if (!typeIds?.length) return "Тип";
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

  const filterCategories = useMemo(() => {
    return categories.map((c) => ({ id: c.id, name: c.name }));
  }, [categories]);

  const closeTypeSheet = () => {
    setTypeOpen(false);
    if (reopenFiltersAfterPickerRef.current) {
      reopenFiltersAfterPickerRef.current = false;
      setFiltersOpen(true);
    }
  };

  const closeBrandSheet = () => {
    setBrandOpen(false);
    if (reopenFiltersAfterPickerRef.current) {
      reopenFiltersAfterPickerRef.current = false;
      setFiltersOpen(true);
    }
  };

  /* ── Chevron SVG ── */
  const ChevDown = () => (
    <span className={styles.chev} aria-hidden="true">
      <svg width="11" height="12.57" viewBox="0 0 9 5" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path fillRule="evenodd" clipRule="evenodd" d="M0.237441 0.240947C0.421218 0.0530257 0.719178 0.0530257 0.902954 0.240947L4.09961 3.50971L7.29626 0.240947C7.48004 0.0530257 7.778 0.0530257 7.96178 0.240947C8.14555 0.428869 8.14555 0.73355 7.96178 0.921471L4.43236 4.53049C4.24859 4.71842 3.95063 4.71842 3.76685 4.53049L0.237441 0.921471C0.0536653 0.73355 0.0536653 0.428869 0.237441 0.240947Z" fill="#7E7E7E" />
      </svg>
    </span>
  );

  /* ── Render ── */
  return (
    <div className="lm-app-bg" style={{ minHeight: "var(--tg-viewport-height)" }}>
      <Header showClose={false} showMore={false} hideOnDesktop />
      <div className={styles.container}>
        {/* Search bar + filters sticky group */}
        <div className={showResults ? styles.stickyTop : styles.searchBarWrap}>
        {/* Back button — only in plain browser, not inside Telegram */}
        {showResults && !window.Telegram?.WebApp?.initData ? (
          <div className={styles.desktopBackRow}>
            <button type="button" className={styles.desktopBackBtn} onClick={handleBack} aria-label="Назад">
              <svg width="9" height="16" viewBox="0 0 9 16" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M8 1L1 8L8 15" stroke="#111111" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
              Назад
            </button>
          </div>
        ) : null}
        <SearchBar
          isSearchActivated={isSearchActivated}
          isSearchClear={() => {
            setHasTyped(false);
            setQuery("");
            setSubmittedQuery("");
            setSearchActivated(false);
            setIsFocused(false);
          }}
          inputRef={inputRef}
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setHasTyped(true);
            setSearchActivated(true);
          }}
          onFocus={() => {
            if (blurCloseTimerRef.current) {
              window.clearTimeout(blurCloseTimerRef.current);
              blurCloseTimerRef.current = null;
            }
            setIsFocused(true);
            setHasTyped(false);
          }}
          onBlur={() => {
            blurCloseTimerRef.current = window.setTimeout(() => {
              setIsFocused(false);
              blurCloseTimerRef.current = null;
            }, 150);
          }}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              commitSearch(query);
            }
          }}
          inputMode="search"
          enterKeyHint="search"
          placeholder="Поиск"
        />
        {/* Filter chips inside sticky group when in results mode */}
        {showResults && !showOverlay ? (
            <div className={cn(styles.filtersBarInner, filtersBarHidden ? styles.filtersBarHidden : null)} aria-label="Фильтры">
              <div className={cn(styles.filtersRow, "scrollbar-hide")}>
                {/* Sort icon */}
                <button type="button" className={cn(styles.iconChip, sort !== "popular" ? styles.iconChipActive : null)} aria-label="Сортировка" onClick={() => setSortOpen(true)}>
                  <svg width="14" height="11" viewBox="0 0 14 11" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M6.94122 9.58731H0.766235M13.1162 5.17661H0.766235M13.1162 0.7659H0.766235" stroke={sort !== "popular" ? "white" : "black"} strokeWidth="1.53178" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </button>
                {/* Filters icon */}
                <button type="button" className={cn(styles.iconChip, activeFilterCount > 0 ? styles.iconChipActive : null)} aria-label="Фильтры" onClick={() => setFiltersOpen(true)}>
                  <svg width="17" height="11" viewBox="0 0 17 11" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M10.1113 7.97225H16.1002M0.700195 7.97225H2.41131M2.41131 7.97225C2.41131 9.15352 3.36892 10.1111 4.5502 10.1111C5.73148 10.1111 6.68909 9.15352 6.68909 7.97225C6.68909 6.79097 5.73148 5.83335 4.5502 5.83335C3.36892 5.83335 2.41131 6.79097 2.41131 7.97225ZM15.2447 2.8389H16.1002M0.700195 2.8389H6.68909M12.2502 4.9778C11.0689 4.9778 10.1113 4.02018 10.1113 2.8389C10.1113 1.65763 11.0689 0.700012 12.2502 0.700012C13.4315 0.700012 14.3891 1.65763 14.3891 2.8389C14.3891 4.02018 13.4315 4.9778 12.2502 4.9778Z" stroke={activeFilterCount > 0 ? "white" : "black"} strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                  {activeFilterCount > 0 ? <span className={styles.iconChipBadge}>{activeFilterCount}</span> : null}
                </button>
                {/* Category chip */}
                <button type="button" className={cn(styles.filterChip, activeCategoryId != null ? styles.filterChipActive : null)} onClick={() => setCategoryOpen(true)}>
                  <span>{categoryChipLabel}</span>
                  {activeCategoryId != null ? (
                    <span className={styles.selectedChipX} role="button" onClick={(e) => { e.stopPropagation(); setActiveCategoryId(null); }}><img src="/icons/global/markXBlack.svg" alt="" /></span>
                  ) : <ChevDown />}
                </button>
                {/* Type chip */}
                <button type="button" className={cn(styles.filterChip, typeIds?.length ? styles.filterChipActive : null)} onClick={() => setTypeOpen(true)}>
                  <span>{typeChipLabel}</span>
                  {typeIds?.length ? (
                    <span className={styles.selectedChipX} role="button" onClick={(e) => { e.stopPropagation(); setTypeIds([]); }}><img src="/icons/global/markXBlack.svg" alt="" /></span>
                  ) : <ChevDown />}
                </button>
                {/* Brand chip */}
                <button type="button" className={cn(styles.filterChip, brandIds?.length ? styles.filterChipActive : null)} onClick={() => setBrandOpen(true)}>
                  <span>{brandChipLabel}</span>
                  {brandIds?.length ? (
                    <span className={styles.selectedChipX} role="button" onClick={(e) => { e.stopPropagation(); setBrandIds([]); }}><img src="/icons/global/markXBlack.svg" alt="" /></span>
                  ) : <ChevDown />}
                </button>
                {/* Price chip */}
                <button type="button" className={cn(styles.filterChip, (priceRange?.min != null || priceRange?.max != null) ? styles.filterChipActive : null)} onClick={() => setPriceOpen(true)}>
                  <span>{priceLabel}</span>
                  {priceRange?.min != null || priceRange?.max != null ? (
                    <span className={styles.selectedChipX} role="button" onClick={(e) => { e.stopPropagation(); setPriceRange({ min: null, max: null }); }}><img src="/icons/global/markXBlack.svg" alt="" /></span>
                  ) : <ChevDown />}
                </button>
                {/* Original chip */}
                <button type="button" className={cn(styles.filterChip, original ? styles.filterChipActive : null)} onClick={() => setOriginal(!original)}>
                  <span>Оригинал</span>
                  {original ? (
                    <span className={styles.selectedChipX} role="button" onClick={(e) => { e.stopPropagation(); setOriginal(false); }}><img src="/icons/global/markXBlack.svg" alt="" /></span>
                  ) : null}
                </button>
                {/* Delivery chip */}
                <button type="button" className={cn(styles.filterChip, hasDeliveryFilter ? styles.filterChipActive : null)} onClick={() => setDeliveryOpen(true)}>
                  <span>{deliveryChipLabel}</span>
                  {hasDeliveryFilter ? (
                    <span className={styles.selectedChipX} role="button" onClick={(e) => { e.stopPropagation(); setDelivery({ inStock: false, fromChina: false }); }}><img src="/icons/global/markXBlack.svg" alt="" /></span>
                  ) : <ChevDown />}
                </button>
              </div>
            </div>
        ) : null}
        </div>

        {/* Category tabs — only in home mode */}
        {!showOverlay && isHomeMode ? (
          <div className={styles.categoryTabsWrap}>
            <CategoryTabs
              activeCategoryId={activeCategoryId}
              onCategoryChange={handleCategoryChange}
            />
          </div>
        ) : null}

        {/* Search overlay (suggestions / history) */}
        {showOverlay ? (
          <SearchOverlay
            query={query}
            debouncedQuery={debouncedQuery}
            showSuggestions={showSuggestions}
            onSelectSuggestion={commitSearch}
            onBackdropClick={() => {
              setIsFocused(false);
              inputRef.current?.blur?.();
            }}
          />
        ) : null}

        {/* ── HOME MODE ── */}
        {isHomeMode ? (
          <>
            <FriendsSection />

            <div className={styles.sectionSpacing}>
              <HomeDeliveryStatusCard />
              <HomeDeliveryStatusCard />
            </div>

            {recentProducts.length > 0 || isLatestInitialLoading ? (
              <ProductSection
                title="Только что купили"
                products={recentProducts}
                onToggleFavorite={toggleFavorite}
                favoriteItemIds={favoriteItemIds}
                layout="horizontal"
                isLoading={isLatestInitialLoading}
                skeletonCount={5}
                viewAllHref="https://t.me/loyaltystream"
              />
            ) : null}

            {recommendedProducts.length > 0 || isRecommendedInitialLoading ? (
              <ProductSection
                title="Для вас"
                products={recommendedProducts}
                onToggleFavorite={toggleFavorite}
                favoriteItemIds={favoriteItemIds}
                layout="grid"
                isLoading={isRecommendedInitialLoading}
                skeletonCount={6}
              />
            ) : null}

            {isRecommendedLoadingMore || isRecommendedRetryPending ? (
              <div className={styles.loadMore} aria-live="polite" aria-busy="true">
                <div className={styles.spinner} aria-hidden="true" />
                <div className={styles.loadMoreText}>
                  {loadMoreError?.transient && !loadMoreError?.exhausted
                    ? `Повторная попытка (${loadMoreError.attempt}/${MAX_AUTO_RETRIES})…`
                    : "Загрузка…"}
                </div>
              </div>
            ) : loadMoreError?.exhausted ? (
              <div className={styles.loadMore} role="alert" aria-live="polite">
                <div className={styles.loadMoreText}>
                  Не удалось загрузить больше товаров.
                </div>
                <button
                  type="button"
                  className={styles.retryBtn}
                  onClick={retryLoadMore}
                >
                  Повторить
                </button>
              </div>
            ) : null}

            <div ref={sentinelRef} style={{ height: 1 }} aria-hidden="true" />
          </>
        ) : null}

        {/* ── FILTERED / SEARCH RESULTS MODE ── */}
        {!isHomeMode && !showOverlay ? (
          <section className={styles.results}>
            {filteredProducts.length === 0 && !isFilteredLoading ? (
              <div className={styles.empty} role="status" aria-live="polite">
                <div className={styles.emptyTitle}>Ничего не найдено</div>
                <div className={styles.emptySubtitle}>Но можно поискать что-то другое</div>
              </div>
            ) : (
              <ProductSection
                title=""
                products={filteredProducts}
                onToggleFavorite={toggleFavorite}
                favoriteItemIds={favoriteItemIds}
                layout="grid"
                isLoading={isFilteredLoading}
                isViewed={true}
              />
            )}
          </section>
        ) : null}

        {!isFocused ? <Footer /> : null}

        {/* ── Bottom Sheets ── */}
        <SelectSheet
          open={categoryOpen}
          onClose={() => setCategoryOpen(false)}
          title="Категория"
          options={categoryOptions}
          value={activeCategoryId}
          onApply={(v) => setActiveCategoryId(v ?? null)}
        />

        <SelectSheet
          open={deliveryOpen}
          onClose={() => setDeliveryOpen(false)}
          title="Доставка"
          options={[
            { value: "fromChina", label: "Из Китая" },
            { value: "inStock", label: "Из наличия" },
          ]}
          multiple
          control="check"
          value={[
            ...(delivery.fromChina ? ["fromChina"] : []),
            ...(delivery.inStock ? ["inStock"] : []),
          ]}
          onApply={(v) => {
            const arr = Array.isArray(v) ? v : [];
            setDelivery({
              fromChina: arr.includes("fromChina"),
              inStock: arr.includes("inStock"),
            });
          }}
        />

        <SelectSheet
          open={sortOpen}
          onClose={() => setSortOpen(false)}
          title="Показывать сначала"
          options={[
            { value: "popular", label: "Популярные" },
            { value: "price_asc", label: "Подешевле" },
            { value: "price_desc", label: "Подороже" },
          ]}
          value={sort}
          onApply={(v) => setSort(v)}
        />

        <SelectSheet
          open={typeOpen}
          onClose={closeTypeSheet}
          title="Тип"
          options={typeOptions}
          multiple
          control="check"
          showSelectedChips
          value={typeIds}
          onApply={(v) => setTypeIds(Array.isArray(v) ? v : [])}
          isTypeModule={true}
        />

        <SelectSheet
          open={brandOpen}
          onClose={closeBrandSheet}
          title="Бренд"
          options={brandOptions}
          multiple
          value={brandIds}
          searchable
          searchPlaceholder="Найти бренд"
          groupBy="alpha"
          onApply={(v) => setBrandIds(Array.isArray(v) ? v : [])}
        />

        <PriceSheet
          open={priceOpen}
          onClose={() => setPriceOpen(false)}
          title="Цена"
          value={priceRange}
          minPlaceholder={priceBounds.min}
          maxPlaceholder={priceBounds.max}
          onApply={(v) => setPriceRange(v)}
        />

        <FiltersSheet
          open={filtersOpen}
          onClose={() => setFiltersOpen(false)}
          categories={filterCategories}
          value={{
            categoryIds: activeCategoryId != null ? [activeCategoryId] : [],
            types: typeIds.map((id) => typeIdToName.get(String(id)) ?? String(id)),
            brands: brandIds.map((id) => brandIdToName.get(String(id)) ?? String(id)),
            priceRange,
            delivery,
            original,
          }}
          priceBounds={priceBounds}
          onApply={(next) => {
            const catIds = Array.isArray(next.categoryIds) ? next.categoryIds : [];
            setActiveCategoryId(catIds.length ? catIds[catIds.length - 1] : null);
            if (Array.isArray(next.types) && next.types.length === 0) setTypeIds([]);
            if (Array.isArray(next.brands) && next.brands.length === 0) setBrandIds([]);
            setPriceRange(next.priceRange ?? { min: null, max: null });
            setDelivery(next.delivery ?? { inStock: false, fromChina: false });
            setOriginal(Boolean(next.original));
          }}
          onOpenTypePicker={() => {
            reopenFiltersAfterPickerRef.current = true;
            setFiltersOpen(false);
            setTypeOpen(true);
          }}
          onOpenBrandPicker={() => {
            reopenFiltersAfterPickerRef.current = true;
            setFiltersOpen(false);
            setBrandOpen(true);
          }}
        />
      </div>
    </div>
  );
}
