'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  keepPreviousData,
  useMutation,
  useQuery,
  useQueryClient,
} from '@tanstack/react-query';
import { i18n } from '@/shared/lib/utils';
import {
  PRODUCT_STATUS_LABELS,
  changeProductStatus,
  deleteProduct as apiDeleteProduct,
  fetchProducts,
  productKeys,
} from '@/entities/product';

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
  const queryClient = useQueryClient();

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
  const [statusError, setStatusError] = useState(null);

  // Derived server params
  const statusParam = activeTab === 'all' ? undefined : activeTab;
  const brandParam = brandFilter === 'all' ? undefined : brandFilter;
  const offset = (page - 1) * perPage;

  const listFilters = useMemo(
    () => ({
      offset,
      limit: perPage,
      status: statusParam,
      brandId: brandParam,
      sortBy,
    }),
    [offset, perPage, statusParam, brandParam, sortBy],
  );

  // -----------------------------------------------------------------------
  // Server state — list + counts via TanStack Query
  // -----------------------------------------------------------------------
  const {
    data: listData,
    isPending: listPending,
    error: listError,
    refetch: refetchList,
  } = useQuery({
    queryKey: productKeys.list(listFilters),
    queryFn: () => fetchProducts(listFilters),
    placeholderData: keepPreviousData,
  });

  const items = useMemo(
    () => (listData?.items ?? []).map(mapProduct),
    [listData],
  );
  const total = listData?.total ?? 0;
  const brands = useMemo(() => listData?._lookup?.brands ?? [], [listData]);

  const loading = listPending && !listData;
  const error = listError
    ? listError.message || 'Не удалось загрузить товары'
    : null;

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

  useEffect(() => {
    setOpenMenuId(null);
  }, [page]);

  useEffect(() => {
    if (!statusError) return;
    const t = setTimeout(() => setStatusError(null), 4000);
    return () => clearTimeout(t);
  }, [statusError]);

  const reloadAll = useCallback(() => {
    refetchList();
  }, [refetchList]);

  // -----------------------------------------------------------------------
  // Cache invalidation helper — called from mutations on success
  // -----------------------------------------------------------------------
  const invalidateProducts = useCallback(
    (productId) => {
      queryClient.invalidateQueries({ queryKey: productKeys.lists() });
      if (productId) {
        queryClient.invalidateQueries({
          queryKey: productKeys.detail(productId),
        });
      }
    },
    [queryClient],
  );

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

  const totalFiltered = searchActive ? visible.length : total;
  const pages = searchActive ? 1 : Math.max(1, Math.ceil(total / perPage));

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
  // Mutations — single-product status / archive / delete
  // -----------------------------------------------------------------------
  const statusMutation = useMutation({
    mutationFn: ({ id, targetStatus }) => changeProductStatus(id, targetStatus),
    onSuccess: (_, { id }) => invalidateProducts(id),
    onError: (err, { targetStatus }) => {
      const label = PRODUCT_STATUS_LABELS[targetStatus] ?? targetStatus;
      setStatusError(err.message || `Не удалось сменить статус на «${label}»`);
    },
    onSettled: () => setOpenMenuId(null),
  });

  const archiveMutation = useMutation({
    mutationFn: (id) => changeProductStatus(id, 'archived'),
    onSuccess: (_, id) => {
      invalidateProducts(id);
      setSelectedIds((prev) => {
        const next = new Set(prev);
        next.delete(id);
        return next;
      });
    },
    onError: (err) =>
      setStatusError(err.message || 'Не удалось архивировать товар'),
    onSettled: () => setArchiveTarget(null),
  });

  /**
   * Audit 3.2 — optimistic delete.
   *
   * Pre-fix the row stayed visible until the mutation landed and the
   * subsequent `invalidateProducts()` round-trip refetched the page,
   * which made the "Удалить" click feel laggy. Now we snapshot every
   * cached `productKeys.list(...)` payload, splice the deleted row
   * out of each one synchronously, and restore the snapshots on
   * `onError`. Sticky `setQueryData` survives until the actual
   * invalidation in `onSettled` repopulates with fresh data.
   */
  const deleteMutation = useMutation({
    mutationFn: (id) => apiDeleteProduct(id),
    onMutate: async (id) => {
      await queryClient.cancelQueries({ queryKey: productKeys.lists() });
      const snapshots = queryClient.getQueriesData({
        queryKey: productKeys.lists(),
      });
      for (const [key, data] of snapshots) {
        if (!data?.items) continue;
        queryClient.setQueryData(key, {
          ...data,
          items: data.items.filter((p) => p.id !== id),
          total:
            typeof data.total === 'number'
              ? Math.max(0, data.total - 1)
              : data.total,
        });
      }
      return { snapshots };
    },
    onError: (err, _id, context) => {
      for (const [key, data] of context?.snapshots ?? []) {
        queryClient.setQueryData(key, data);
      }
      setStatusError(err.message || 'Не удалось удалить товар');
    },
    onSuccess: (_, id) => {
      // Drop the cached detail so that navigating back to a deleted product
      // doesn't briefly serve stale data before the inevitable 404.
      queryClient.removeQueries({ queryKey: productKeys.detail(id) });
      setSelectedIds((prev) => {
        const next = new Set(prev);
        next.delete(id);
        return next;
      });
    },
    onSettled: () => {
      // Always re-validate against backend so any optimistic divergence
      // is reconciled — even on success the `total` arithmetic might
      // drift from server-side counts (e.g. concurrent inserts).
      invalidateProducts();
      setDeleteTarget(null);
    },
  });

  const { mutate: mutateStatus } = statusMutation;
  const updateProductStatus = useCallback(
    (id, targetStatus) => {
      setStatusError(null);
      mutateStatus({ id, targetStatus });
    },
    [mutateStatus],
  );

  const { mutate: mutateArchive } = archiveMutation;
  const archiveProduct = useCallback(
    (id) => {
      setStatusError(null);
      mutateArchive(id);
    },
    [mutateArchive],
  );

  const requestArchiveProduct = useCallback((product) => {
    setArchiveTarget(product);
    setOpenMenuId(null);
  }, []);

  const requestDeleteProduct = useCallback((product) => {
    setDeleteTarget(product);
    setOpenMenuId(null);
  }, []);

  const { mutate: mutateDelete } = deleteMutation;
  const confirmDeleteProduct = useCallback(
    (id) => {
      setStatusError(null);
      mutateDelete(id);
    },
    [mutateDelete],
  );

  // -----------------------------------------------------------------------
  // Bulk actions — fan out, then invalidate once.
  // Wrapped in useMutation so concurrent clicks are blocked via `isPending`
  // and consumers can read a unified bulk-action loading state.
  // -----------------------------------------------------------------------
  const selectedCount = selectedIds.size;

  const bulkDeleteMutation = useMutation({
    mutationFn: async (ids) => {
      const results = await Promise.allSettled(
        ids.map((id) => apiDeleteProduct(id)),
      );
      return { ids, results };
    },
    // Audit 3.2 — same optimistic strategy as the single-delete path:
    // splice every deleted id out of every cached list snapshot, then
    // reconcile in `onSettled`. `Promise.allSettled` means individual
    // failures don't bring back the whole list — the final invalidate
    // pulls a fresh server snapshot and any rows that ultimately
    // failed to delete reappear automatically.
    onMutate: async (ids) => {
      await queryClient.cancelQueries({ queryKey: productKeys.lists() });
      const snapshots = queryClient.getQueriesData({
        queryKey: productKeys.lists(),
      });
      const idSet = new Set(ids);
      for (const [key, data] of snapshots) {
        if (!data?.items) continue;
        const remaining = data.items.filter((p) => !idSet.has(p.id));
        queryClient.setQueryData(key, {
          ...data,
          items: remaining,
          total:
            typeof data.total === 'number'
              ? Math.max(0, data.total - (data.items.length - remaining.length))
              : data.total,
        });
      }
      return { snapshots };
    },
    onSuccess: ({ ids, results }) => {
      const failed = results.filter((r) => r.status === 'rejected').length;
      if (failed > 0) {
        setStatusError(`Не удалось удалить ${failed} из ${ids.length} товаров`);
      }
      results.forEach((r, idx) => {
        if (r.status === 'fulfilled') {
          queryClient.removeQueries({
            queryKey: productKeys.detail(ids[idx]),
          });
        }
      });
      setSelectedIds(new Set());
      setOpenMenuId(null);
    },
    // mutationFn is wrapped in Promise.allSettled, so reaching this branch
    // means the wrapper itself crashed (e.g. invariant in apiClient setup).
    // Restore the snapshots so the toolbar exits pending state without
    // leaving the UI in a half-deleted state.
    onError: (err, _ids, context) => {
      for (const [key, data] of context?.snapshots ?? []) {
        queryClient.setQueryData(key, data);
      }
      setStatusError(err?.message || 'Не удалось выполнить массовое удаление');
    },
    onSettled: () => {
      invalidateProducts();
    },
  });

  const bulkArchiveMutation = useMutation({
    mutationFn: async (ids) => {
      const results = await Promise.allSettled(
        ids.map((id) => changeProductStatus(id, 'archived')),
      );
      return { ids, results };
    },
    onSuccess: ({ ids, results }) => {
      const failed = results.filter((r) => r.status === 'rejected').length;
      if (failed > 0) {
        setStatusError(
          `Не удалось архивировать ${failed} из ${ids.length} товаров`,
        );
      }
      setSelectedIds(new Set());
      setOpenMenuId(null);
      invalidateProducts();
    },
    onError: (err) => {
      setStatusError(err?.message || 'Не удалось выполнить массовую архивацию');
    },
  });

  const { mutate: bulkDelete, isPending: bulkDeleting } = bulkDeleteMutation;
  const deleteSelected = useCallback(() => {
    if (!selectedCount || bulkDeleting) return;
    setStatusError(null);
    bulkDelete([...selectedIds]);
  }, [selectedCount, selectedIds, bulkDelete, bulkDeleting]);

  const { mutate: bulkArchive, isPending: bulkArchiving } = bulkArchiveMutation;
  const archiveSelected = useCallback(() => {
    if (!selectedCount || bulkArchiving) return;
    setStatusError(null);
    bulkArchive([...selectedIds]);
  }, [selectedCount, selectedIds, bulkArchive, bulkArchiving]);

  const bulkActionPending = bulkDeleting || bulkArchiving;

  return {
    // Data
    items,
    visible,
    loading,
    error,
    statusError,
    total,

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

    // Bulk action loading state (single source of truth for BulkBar UX)
    bulkActionPending,

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
