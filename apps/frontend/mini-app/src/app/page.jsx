'use client';

import { Suspense, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';

import SearchBar from '@/features/search';
import SearchOverlay from '@/features/search';
import Header from '@/widgets/Header';
import Footer from '@/widgets/Footer';
import CategoryTabs from '@/features/home-feed/ui/CategoryTabs';
import ProductSection from '@/entities/product';
import SelectSheet from '@/features/search';
import PriceSheet from '@/features/search';
import FiltersSheet from '@/features/search';
import { mapProductCard } from '@/entities/product';
import { useGetTrendingProductsQuery } from '@/entities/product';
import { useCreateSearchHistoryMutation } from '@/features/search';
import { useItemFavorites } from '@/features/favorites';
import { useBackHandlerStore } from '@/features/telegram-api';
import { normalizeSearchText } from '@/features/home-feed/lib/utils';
import { useHomeSearch } from '@/features/home-feed/model/useHomeSearch';
import { useHomeFilters } from '@/features/home-feed/model/useHomeFilters';
import { useForYouFeed } from '@/features/home-feed';
import { useFilteredProducts } from '@/features/home-feed/model/useFilteredProducts';

import FilterChipsBar from '@/widgets/HomePage/FilterChipsBar';
import HomeFeed from '@/widgets/HomePage/HomeFeed';
import styles from './page.module.css';

/**
 * Home page (`/`) — catalog/search/filter.
 *
 * Audit #1 (god-component decomposition): this used to be a single
 * 1370-line file. Now it's an orchestrator:
 *  • pure helpers       → `lib/home/utils.js`
 *  • search state       → `lib/home/useHomeSearch.js`
 *  • filter domain      → `lib/home/useHomeFilters.js`
 *  • "Для вас" feed     → `lib/home/useForYouFeed.js`
 *  • filtered results   → `lib/home/useFilteredProducts.js`
 *  • presentation       → `./_home/{FilterChipsBar,HomeFeed}.jsx`
 *
 * Glue that remains on the page: sheet open states (7), `commitSearch`,
 * `resetToHome`, `handleCategoryChange`, `handleBack` + registration,
 * init-from-URL — all of these touch the search AND filter state.
 */

export default function HomePage() {
  return (
    <Suspense>
      <Home />
    </Suspense>
  );
}

function Home() {
  const { favoriteItemIds, toggleFavorite } = useItemFavorites('product');
  const searchParams = useSearchParams();
  const router = useRouter();

  const initializedFromUrl = useRef(false);
  const cameFromExternalSearch = useRef(false);
  const reopenFiltersAfterPickerRef = useRef(false);
  const lastScrollY = useRef(0);
  const [filtersBarHidden, setFiltersBarHidden] = useState(false);

  /* ── Search state (with debounce) ── */
  const {
    inputRef,
    blurCloseTimerRef,
    query,
    setQuery,
    submittedQuery,
    setSubmittedQuery,
    isFocused,
    setIsFocused,
    setHasTyped,
    debouncedQuery,
    isSearchActivated,
    setSearchActivated,
    showSuggestions,
  } = useHomeSearch();

  /* ── Sheet open state ── */
  const [isSortOpen, setIsSortOpen] = useState(false);
  const [isFiltersOpen, setIsFiltersOpen] = useState(false);
  const [isTypeOpen, setIsTypeOpen] = useState(false);
  const [isBrandOpen, setIsBrandOpen] = useState(false);
  const [isPriceOpen, setIsPriceOpen] = useState(false);
  const [isCategoryOpen, setIsCategoryOpen] = useState(false);
  const [isDeliveryOpen, setIsDeliveryOpen] = useState(false);

  /* ── Filter domain ── */
  const {
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
    defaultCategoryId,
    typeOptions,
    brandOptions,
    categoryOptions,
    filterCategories,
    categoryChipLabel,
    typeChipLabel,
    brandChipLabel,
    priceLabel,
    deliveryChipLabel,
    hasDeliveryFilter,
    activeFilterCount,
    brandIdToName,
    typeIdToName,
    showResults,
    categoriesRef,
    brandsRef,
  } = useHomeFilters({ submittedQuery, isFiltersOpen, isTypeOpen, isBrandOpen });

  /* ── Derived mode ── */
  const showOverlay = isFocused;
  const isHomeMode = !showResults && !showOverlay;

  /* ── Data feeds ── */
  const { filteredProducts, isFilteredLoading, priceBounds } = useFilteredProducts({
    submittedQuery,
    activeCategoryId,
    typeIds,
    brandIds,
    priceRange,
    sort,
    defaultCategoryId,
  });

  const {
    recommendedProducts,
    sentinelRef,
    isRecommendedInitialLoading,
    isRecommendedLoadingMore,
    isRecommendedRetryPending,
    loadMoreError,
    retryLoadMore,
  } = useForYouFeed({ isHomeMode });

  // "Только что купили" — trending (in placeholder form).
  const {
    data: latestData,
    isLoading: isLatestLoading,
    isFetching: isLatestFetching,
  } = useGetTrendingProductsQuery({ limit: 10, window: 'weekly' });
  const isLatestInitialLoading =
    Boolean(isLatestLoading || isLatestFetching) &&
    (!Array.isArray(latestData) || latestData.length === 0);
  const recentProducts = useMemo(() => {
    const rows = Array.isArray(latestData) ? latestData : [];
    return rows.map((p) => mapProductCard(p, null)).filter(Boolean);
  }, [latestData]);

  /* ── Reset to home ── */
  const resetToHome = useCallback(() => {
    setQuery('');
    setSubmittedQuery('');
    setIsFocused(false);
    setHasTyped(false);
    setSearchActivated(false);
    setActiveCategoryId(null);
    setTypeIds([]);
    setBrandIds([]);
    setPriceRange({ min: null, max: null });
    setDelivery({ inStock: false, fromChina: false });
    setOriginal(false);
    setSort('popular');
    inputRef.current?.blur?.();
  }, [
    setQuery,
    setSubmittedQuery,
    setIsFocused,
    setHasTyped,
    setSearchActivated,
    setActiveCategoryId,
    setTypeIds,
    setBrandIds,
    setPriceRange,
    setDelivery,
    setOriginal,
    setSort,
    inputRef,
  ]);

  /* ── Initialize filters from URL params (e.g. from catalog page) ── */
  useEffect(() => {
    if (initializedFromUrl.current) return;
    initializedFromUrl.current = true;

    const categoryId = searchParams.get('category_id');
    const typeId = searchParams.get('type_id');
    const brandId = searchParams.get('brand_id');
    const q = searchParams.get('query');
    const openSearch = searchParams.get('search');

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
      window.history.replaceState({}, '', '/');
    }
  }, [
    searchParams,
    setActiveCategoryId,
    setTypeIds,
    setBrandIds,
    setQuery,
    setSubmittedQuery,
    setSearchActivated,
    setIsFocused,
    inputRef,
  ]);

  /* ── Telegram BackButton & Header back handler ── */
  const handleBack = useCallback(() => {
    // 1. If any sheet is open → close it
    if (isFiltersOpen) {
      setIsFiltersOpen(false);
      return;
    }
    if (isSortOpen) {
      setIsSortOpen(false);
      return;
    }
    if (isTypeOpen) {
      setIsTypeOpen(false);
      return;
    }
    if (isBrandOpen) {
      setIsBrandOpen(false);
      return;
    }
    if (isPriceOpen) {
      setIsPriceOpen(false);
      return;
    }
    if (isCategoryOpen) {
      setIsCategoryOpen(false);
      return;
    }
    if (isDeliveryOpen) {
      setIsDeliveryOpen(false);
      return;
    }
    // 2. If came from external page (e.g. catalog) → go back in history
    if (cameFromExternalSearch.current) {
      cameFromExternalSearch.current = false;
      router.back();
      return;
    }
    // 3. If search/filters active → go home
    resetToHome();
  }, [
    isFiltersOpen,
    isSortOpen,
    isTypeOpen,
    isBrandOpen,
    isPriceOpen,
    isCategoryOpen,
    isDeliveryOpen,
    resetToHome,
    router,
  ]);

  const setHomeBack = useBackHandlerStore((s) => s.setHomeBack);
  const clearHomeBack = useBackHandlerStore((s) => s.clearHomeBack);
  useEffect(() => {
    if (
      !isHomeMode ||
      isFiltersOpen ||
      isSortOpen ||
      isTypeOpen ||
      isBrandOpen ||
      isPriceOpen ||
      isCategoryOpen ||
      isDeliveryOpen
    ) {
      setHomeBack(handleBack);
    } else {
      clearHomeBack();
    }
    return () => clearHomeBack();
  }, [
    isHomeMode,
    handleBack,
    isFiltersOpen,
    isSortOpen,
    isTypeOpen,
    isBrandOpen,
    isPriceOpen,
    isCategoryOpen,
    isDeliveryOpen,
    setHomeBack,
    clearHomeBack,
  ]);

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
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  /* ── Search commit (search + filter glue) ── */
  const [createSearchHistory] = useCreateSearchHistoryMutation();

  const commitSearch = useCallback(
    (value) => {
      const next = String(value || '').trim();
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
      const nq = normalizeSearchText(next);
      const matchedBrand = brandsRef.current.find((b) => normalizeSearchText(b.name) === nq);
      if (matchedBrand) setBrandIds([matchedBrand.id]);
      const matchedCategory = categoriesRef.current.find((c) => normalizeSearchText(c.name) === nq);
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
      blurCloseTimerRef,
      inputRef,
      brandsRef,
      categoriesRef,
      setIsFocused,
      setHasTyped,
      setQuery,
      setSubmittedQuery,
      setBrandIds,
      setActiveCategoryId,
    ]
  );

  /* ── Category tab change (search + filter glue) ── */
  const handleCategoryChange = useCallback(
    (categoryId) => {
      setActiveCategoryId(categoryId);
      // Reset sub-filters when switching category
      setTypeIds([]);
      setBrandIds([]);
      setPriceRange({ min: null, max: null });
      setDelivery({ inStock: false, fromChina: false });
      setOriginal(false);
      setSort('popular');
      // Clear search when going back to "Для вас"
      if (categoryId == null) {
        setSubmittedQuery('');
        setQuery('');
      }
    },
    [
      setActiveCategoryId,
      setTypeIds,
      setBrandIds,
      setPriceRange,
      setDelivery,
      setOriginal,
      setSort,
      setSubmittedQuery,
      setQuery,
    ]
  );

  /* ── Sheet helpers ── */
  const handleOpenSheet = (name) => {
    if (name === 'sort') setIsSortOpen(true);
    else if (name === 'filters') setIsFiltersOpen(true);
    else if (name === 'category') setIsCategoryOpen(true);
    else if (name === 'type') setIsTypeOpen(true);
    else if (name === 'brand') setIsBrandOpen(true);
    else if (name === 'price') setIsPriceOpen(true);
    else if (name === 'delivery') setIsDeliveryOpen(true);
  };

  const handleClearFilter = (name) => {
    if (name === 'category') setActiveCategoryId(null);
    else if (name === 'type') setTypeIds([]);
    else if (name === 'brand') setBrandIds([]);
    else if (name === 'price') setPriceRange({ min: null, max: null });
    else if (name === 'original') setOriginal(false);
    else if (name === 'delivery') setDelivery({ inStock: false, fromChina: false });
  };

  const closeTypeSheet = () => {
    setIsTypeOpen(false);
    if (reopenFiltersAfterPickerRef.current) {
      reopenFiltersAfterPickerRef.current = false;
      setIsFiltersOpen(true);
    }
  };

  const closeBrandSheet = () => {
    setIsBrandOpen(false);
    if (reopenFiltersAfterPickerRef.current) {
      reopenFiltersAfterPickerRef.current = false;
      setIsFiltersOpen(true);
    }
  };

  /* ── Render ── */
  return (
    <div className="lm-app-bg" style={{ minHeight: 'var(--tg-viewport-height)' }}>
      <Header showClose={false} showMore={false} hideOnDesktop />
      <div className={styles.container}>
        {/* Search bar + filters sticky group */}
        <div className={showResults ? styles.stickyTop : styles.searchBarWrap}>
          {/* Back button — only in plain browser, not inside Telegram */}
          {showResults && !window.Telegram?.WebApp?.initData ? (
            <div className={styles.desktopBackRow}>
              <button
                type="button"
                className={styles.desktopBackBtn}
                onClick={handleBack}
                aria-label="Назад"
              >
                <svg
                  width="9"
                  height="16"
                  viewBox="0 0 9 16"
                  fill="none"
                  xmlns="http://www.w3.org/2000/svg"
                >
                  <path
                    d="M8 1L1 8L8 15"
                    stroke="#111111"
                    strokeWidth="1.8"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
                Назад
              </button>
            </div>
          ) : null}
          <SearchBar
            isSearchActivated={isSearchActivated}
            isSearchClear={() => {
              setHasTyped(false);
              setQuery('');
              setSubmittedQuery('');
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
              if (e.key === 'Enter') {
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
            <FilterChipsBar
              isFiltersBarHidden={filtersBarHidden}
              sort={sort}
              activeFilterCount={activeFilterCount}
              activeCategoryId={activeCategoryId}
              categoryChipLabel={categoryChipLabel}
              typeIds={typeIds}
              typeChipLabel={typeChipLabel}
              brandIds={brandIds}
              brandChipLabel={brandChipLabel}
              priceRange={priceRange}
              priceLabel={priceLabel}
              isOriginalOnly={original}
              hasDeliveryFilter={hasDeliveryFilter}
              deliveryChipLabel={deliveryChipLabel}
              onOpenSheet={handleOpenSheet}
              onClearFilter={handleClearFilter}
              onToggleOriginal={() => setOriginal(!original)}
            />
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
          <HomeFeed
            recentProducts={recentProducts}
            isLatestInitialLoading={isLatestInitialLoading}
            recommendedProducts={recommendedProducts}
            isRecommendedInitialLoading={isRecommendedInitialLoading}
            isRecommendedLoadingMore={isRecommendedLoadingMore}
            isRecommendedRetryPending={isRecommendedRetryPending}
            loadMoreError={loadMoreError}
            retryLoadMore={retryLoadMore}
            sentinelRef={sentinelRef}
            favoriteItemIds={favoriteItemIds}
            toggleFavorite={toggleFavorite}
          />
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
          open={isCategoryOpen}
          onClose={() => setIsCategoryOpen(false)}
          title="Категория"
          options={categoryOptions}
          value={activeCategoryId}
          onApply={(v) => setActiveCategoryId(v ?? null)}
        />

        <SelectSheet
          open={isDeliveryOpen}
          onClose={() => setIsDeliveryOpen(false)}
          title="Доставка"
          options={[
            { value: 'fromChina', label: 'Из Китая' },
            { value: 'inStock', label: 'Из наличия' },
          ]}
          multiple
          control="check"
          value={[
            ...(delivery.fromChina ? ['fromChina'] : []),
            ...(delivery.inStock ? ['inStock'] : []),
          ]}
          onApply={(v) => {
            const arr = Array.isArray(v) ? v : [];
            setDelivery({
              fromChina: arr.includes('fromChina'),
              inStock: arr.includes('inStock'),
            });
          }}
        />

        <SelectSheet
          open={isSortOpen}
          onClose={() => setIsSortOpen(false)}
          title="Показывать сначала"
          options={[
            { value: 'popular', label: 'Популярные' },
            { value: 'price_asc', label: 'Подешевле' },
            { value: 'price_desc', label: 'Подороже' },
          ]}
          value={sort}
          onApply={(v) => setSort(v)}
        />

        <SelectSheet
          open={isTypeOpen}
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
          open={isBrandOpen}
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
          open={isPriceOpen}
          onClose={() => setIsPriceOpen(false)}
          title="Цена"
          value={priceRange}
          minPlaceholder={priceBounds.min}
          maxPlaceholder={priceBounds.max}
          onApply={(v) => setPriceRange(v)}
        />

        <FiltersSheet
          open={isFiltersOpen}
          onClose={() => setIsFiltersOpen(false)}
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
            setIsFiltersOpen(false);
            setIsTypeOpen(true);
          }}
          onOpenBrandPicker={() => {
            reopenFiltersAfterPickerRef.current = true;
            setIsFiltersOpen(false);
            setIsBrandOpen(true);
          }}
        />
      </div>
    </div>
  );
}
