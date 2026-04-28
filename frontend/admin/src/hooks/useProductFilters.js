'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { i18n } from '@/lib/utils';
import { PRODUCT_STATUS_LABELS } from '@/lib/constants';
import { fetchProducts, fetchProductCounts, changeProductStatus, deleteProduct as apiDeleteProduct } from '@/services/products';

// ---------------------------------------------------------------------------
// Tabs — status-based (matches backend filter + FSM)
// ---------------------------------------------------------------------------
const tabs = [
  { key: 'all', label: 'Все' },
  { key: 'draft', label: 'Черновики' },
  { key: 'enriching', label: 'Обогащение' },
  { key: 'ready_for_review', label: 'На модерации' },
  { key: 'published', label: 'Опубликованные' },
  { key: 'archived', label: 'Архив' },
];

export { tabs };

// ---------------------------------------------------------------------------
// Map enriched backend item → UI shape
// ---------------------------------------------------------------------------
function mapProduct(item) {
  const priceRub = item.minPrice != null ? item.minPrice / 100 : null;

  return {
    id: item.id,
    title: i18n(item.titleI18N, item.slug || 'Без названия'),
    slug: item.slug,
    status: item.status,
    statusLabel: PRODUCT_STATUS_LABELS[item.status] ?? item.status,
    brandId: item.brandId,
    brandName: item.brandName ?? null,
    primaryCategoryId: item.primaryCategoryId,
    categoryName: item.categoryI18N ? i18n(item.categoryI18N) : null,
    createdAt: item.createdAt,
    updatedAt: item.updatedAt,
    addedAt: item.createdAt,
    image: item.image ?? null,
    price: priceRub,
    variantsCount: item.variantsCount ?? 1,
    variantAttrs: item.variantAttrs ?? [],
    sourceUrl: item.sourceUrl ?? null,
    supplierType: item.supplierType ?? null,
    supplierCountry: item.supplierCountry ?? null,
  };
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------
export function useProductFilters() {
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [tabCounts, setTabCounts] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [statusError, setStatusError] = useState(null);

  // Lookup data from BFF (brands for filter dropdown)
  const [brands, setBrands] = useState([]);

  // Server-side filter state
  const [activeTab, setActiveTab] = useState('all');
  const [sortBy, setSortBy] = useState('newest');
  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState(10);
  const [brandFilter, setBrandFilter] = useState('all');

  // Client-side search (debounced)
  const [query, setQuery] = useState('');
  const [debouncedQuery, setDebouncedQuery] = useState('');
  const debounceRef = useRef(null);

  // Debounce search input (300ms)
  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      setDebouncedQuery(query);
    }, 300);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [query]);

  // Selection
  const [selectedIds, setSelectedIds] = useState(() => new Set());
  const [openMenuId, setOpenMenuId] = useState(null);
  const [archiveTarget, setArchiveTarget] = useState(null);
  const [deleteTarget, setDeleteTarget] = useState(null);

  // Stale request guard
  const fetchIdRef = useRef(0);

  // Derived server params
  const statusParam = activeTab === 'all' ? undefined : activeTab;
  const brandParam = brandFilter === 'all' ? undefined : brandFilter;
  const offset = (page - 1) * perPage;

  // -----------------------------------------------------------------------
  // Data loading — brand_id is now server-side
  // -----------------------------------------------------------------------

  const loadTabCounts = useCallback(async () => {
    try {
      const counts = await fetchProductCounts();
      setTabCounts(counts);
    } catch {
      // non-critical — don't block UI
    }
  }, []);

  const loadProducts = useCallback(async () => {
    const id = ++fetchIdRef.current;
    setLoading(true);
    setError(null);

    try {
      const data = await fetchProducts({
        offset,
        limit: perPage,
        status: statusParam,
        brandId: brandParam,
        sortBy,
      });

      if (id !== fetchIdRef.current) return; // stale

      setItems(data.items.map(mapProduct));
      setTotal(data.total);

      if (data._lookup?.brands?.length) {
        setBrands(data._lookup.brands);
      }
    } catch (err) {
      if (id !== fetchIdRef.current) return;
      setError(err.message || 'Не удалось загрузить товары');
      setItems([]);
      setTotal(0);
    } finally {
      if (id === fetchIdRef.current) {
        setLoading(false);
      }
    }
  }, [offset, perPage, statusParam, brandParam, sortBy]);

  useEffect(() => {
    loadProducts();
    loadTabCounts();
  }, [loadProducts, loadTabCounts]);

  const reloadAll = useCallback(() => {
    loadProducts();
    loadTabCounts();
  }, [loadProducts, loadTabCounts]);

  // Reset page when filter params change
  useEffect(() => {
    setPage(1);
  }, [activeTab, sortBy, perPage, brandFilter]);

  // Reset client-side filters on tab change
  const handleTabChange = useCallback((tab) => {
    setActiveTab(tab);
    setQuery('');
    setDebouncedQuery('');
    setOpenMenuId(null);
  }, []);

  // Close menu on page change
  useEffect(() => {
    setOpenMenuId(null);
  }, [page]);

  // Auto-clear status error after 4s
  useEffect(() => {
    if (!statusError) return;
    const t = setTimeout(() => setStatusError(null), 4000);
    return () => clearTimeout(t);
  }, [statusError]);

  // -----------------------------------------------------------------------
  // Client-side search (only filters current page — backend has no search)
  // -----------------------------------------------------------------------
  const searchActive = debouncedQuery.trim() !== '';

  const visible = useMemo(() => {
    if (!searchActive) return items;

    const q = debouncedQuery.trim().toLowerCase();
    return items.filter(
      (p) =>
        p.title.toLowerCase().includes(q) ||
        (p.brandName && p.brandName.toLowerCase().includes(q)) ||
        (p.categoryName && p.categoryName.toLowerCase().includes(q)),
    );
  }, [items, debouncedQuery, searchActive]);

  // When search is active, totalFiltered is just visible.length (current page only)
  const totalFiltered = searchActive ? visible.length : total;
  const pages = searchActive
    ? 1 // search filters only current page — pagination not meaningful
    : Math.max(1, Math.ceil(total / perPage));

  // -----------------------------------------------------------------------
  // Brand options for filter dropdown
  // -----------------------------------------------------------------------
  const brandOptions = useMemo(() => {
    const opts = [{ value: 'all', label: 'Все бренды' }];
    for (const b of brands) {
      opts.push({
        value: b.id,
        label: b.name,
        searchable: true,
        groupByInitial: true,
      });
    }
    return opts;
  }, [brands]);

  // -----------------------------------------------------------------------
  // Filters meta
  // -----------------------------------------------------------------------
  const hasActiveFilters =
    query.trim() !== '' || sortBy !== 'newest' || brandFilter !== 'all';

  const resetAll = useCallback(() => {
    setQuery('');
    setDebouncedQuery('');
    setSortBy('newest');
    setBrandFilter('all');
    setPage(1);
    setSelectedIds(new Set());
    setOpenMenuId(null);
  }, []);

  const clearSelection = useCallback(() => {
    setSelectedIds(new Set());
  }, []);

  // -----------------------------------------------------------------------
  // Selection
  // -----------------------------------------------------------------------
  const toggleSelection = useCallback((id) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  const allVisibleSelected =
    visible.length > 0 && visible.every((p) => selectedIds.has(p.id));

  const toggleVisibleAll = () => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (allVisibleSelected) visible.forEach((p) => next.delete(p.id));
      else visible.forEach((p) => next.add(p.id));
      return next;
    });
  };

  // -----------------------------------------------------------------------
  // Status change (generic FSM transition) — with error feedback
  // -----------------------------------------------------------------------
  const updateProductStatus = useCallback(
    async (id, targetStatus) => {
      setStatusError(null);
      try {
        await changeProductStatus(id, targetStatus);
      } catch (err) {
        const label =
          PRODUCT_STATUS_LABELS[targetStatus] ?? targetStatus;
        setStatusError(
          err.message || `Не удалось сменить статус на «${label}»`,
        );
      }
      setOpenMenuId(null);
      reloadAll();
    },
    [reloadAll],
  );

  const archiveProduct = useCallback(
    async (id) => {
      setStatusError(null);
      try {
        await changeProductStatus(id, 'archived');
      } catch (err) {
        setStatusError(err.message || 'Не удалось архивировать товар');
      }
      setArchiveTarget(null);
      setSelectedIds((prev) => {
        const next = new Set(prev);
        next.delete(id);
        return next;
      });
      reloadAll();
    },
    [reloadAll],
  );

  const requestArchiveProduct = useCallback((product) => {
    setArchiveTarget(product);
    setOpenMenuId(null);
  }, []);

  const requestDeleteProduct = useCallback((product) => {
    setDeleteTarget(product);
    setOpenMenuId(null);
  }, []);

  const confirmDeleteProduct = useCallback(
    async (id) => {
      setStatusError(null);
      try {
        await apiDeleteProduct(id);
      } catch (err) {
        setStatusError(err.message || 'Не удалось удалить товар');
      }
      setDeleteTarget(null);
      setSelectedIds((prev) => {
        const next = new Set(prev);
        next.delete(id);
        return next;
      });
      reloadAll();
    },
    [reloadAll],
  );

  const selectedCount = selectedIds.size;

  const deleteSelected = useCallback(async () => {
    if (!selectedCount) return;
    setStatusError(null);
    const ids = [...selectedIds];
    const results = await Promise.allSettled(
      ids.map((id) => apiDeleteProduct(id)),
    );
    const failed = results.filter((r) => r.status === 'rejected').length;
    if (failed > 0) {
      setStatusError(
        `Не удалось удалить ${failed} из ${ids.length} товаров`,
      );
    }
    setSelectedIds(new Set());
    setOpenMenuId(null);
    reloadAll();
  }, [selectedCount, selectedIds, reloadAll]);

  const archiveSelected = useCallback(async () => {
    if (!selectedCount) return;
    setStatusError(null);
    const ids = [...selectedIds];
    const results = await Promise.allSettled(
      ids.map((id) => changeProductStatus(id, 'archived')),
    );
    const failed = results.filter((r) => r.status === 'rejected').length;
    if (failed > 0) {
      setStatusError(
        `Не удалось архивировать ${failed} из ${ids.length} товаров`,
      );
    }
    setSelectedIds(new Set());
    setOpenMenuId(null);
    reloadAll();
  }, [selectedCount, selectedIds, reloadAll]);

  return {
    // Data
    items,
    visible,
    loading,
    error,
    statusError,
    total,
    tabCounts,

    // Tabs
    activeTab,
    setActiveTab: handleTabChange,

    // Filter state
    query,
    setQuery,
    searchActive,
    sortBy,
    setSortBy,
    brandFilter,
    setBrandFilter,
    brandOptions,

    // Pagination
    page,
    pages,
    setPage,
    perPage,
    setPerPage,
    totalFiltered,

    // Selection
    selectedIds,
    selectedCount,
    allVisibleSelected,
    toggleSelection,
    toggleVisibleAll,
    clearSelection,

    // Archive
    archiveTarget,
    setArchiveTarget,
    archiveProduct,
    requestArchiveProduct,
    archiveSelected,

    // Delete
    deleteTarget,
    setDeleteTarget,
    confirmDeleteProduct,
    requestDeleteProduct,
    deleteSelected,

    // Status
    updateProductStatus,

    // Menu
    openMenuId,
    setOpenMenuId,

    // Actions
    resetAll,
    hasActiveFilters,
    retry: reloadAll,
  };
}
