'use client';

import { useEffect, useMemo, useState } from 'react';
import dayjs from '@/lib/dayjs';
import { buildFacetOptions } from '@/lib/utils';

const tabs = [
  { key: 'all', label: 'Все' },
  { key: 'china', label: 'Из Китая' },
  { key: 'stock', label: 'Из наличия' },
  { key: 'draft', label: 'Черновики' },
  { key: 'archived', label: 'Архив' },
];

export { tabs };

export function useProductFilters(initialProducts) {
  const [products, setProducts] = useState(initialProducts);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('all');
  const [query, setQuery] = useState('');
  const [selectMode, setSelectMode] = useState(false);
  const [selectedIds, setSelectedIds] = useState(() => new Set());
  const [openMenuId, setOpenMenuId] = useState(null);
  const [category, setCategory] = useState('all');
  const [kind, setKind] = useState('all');
  const [brand, setBrand] = useState('all');
  const [onlyOriginal, setOnlyOriginal] = useState('all');
  const [sortBy, setSortBy] = useState('newest');
  const [page, setPage] = useState(1);
  const [archiveTarget, setArchiveTarget] = useState(null);
  const [dateRange, setDateRange] = useState({
    from: null,
    to: null,
  });

  const hasRange = Boolean(dateRange.from && dateRange.to);

  const baseForFacets = useMemo(
    () => products.filter((p) => p.status !== 'archived'),
    [products],
  );

  const categoryFacet = useMemo(
    () => buildFacetOptions(baseForFacets, (p) => p.category),
    [baseForFacets],
  );
  const kindFacet = useMemo(
    () => buildFacetOptions(baseForFacets, (p) => p.kind),
    [baseForFacets],
  );
  const brandFacet = useMemo(
    () => buildFacetOptions(baseForFacets, (p) => p.brand),
    [baseForFacets],
  );

  const tabCounts = useMemo(() => {
    const base = { all: 0, china: 0, stock: 0, draft: 0, archived: 0 };
    products.forEach((p) => {
      if (p.status !== 'archived') base.all += 1;
      if (p.source === 'china' && p.status !== 'archived') base.china += 1;
      if (p.source === 'stock' && p.status !== 'archived') base.stock += 1;
      if (p.status === 'draft') base.draft += 1;
      if (p.status === 'archived') base.archived += 1;
    });
    return base;
  }, [products]);

  const metrics = useMemo(() => {
    const nonArchived = products.filter((p) => p.status !== 'archived');
    const today = nonArchived.reduce(
      (acc, p) => acc + Math.max(0, Math.round(p.views * 0.03)),
      0,
    );
    const week = nonArchived.reduce(
      (acc, p) => acc + Math.max(0, Math.round(p.views * 0.18)),
      0,
    );
    const month = nonArchived.reduce(
      (acc, p) => acc + Math.max(0, Math.round(p.views * 0.62)),
      0,
    );
    return { today, week, month };
  }, [products]);

  const originalCount = useMemo(
    () => baseForFacets.filter((p) => p.isOriginal).length,
    [baseForFacets],
  );
  const nonOriginalCount = useMemo(
    () => baseForFacets.filter((p) => !p.isOriginal).length,
    [baseForFacets],
  );

  const filtered = useMemo(() => {
    let next = products.slice();

    if (activeTab === 'china')
      next = next.filter(
        (p) => p.source === 'china' && p.status !== 'archived',
      );
    if (activeTab === 'stock')
      next = next.filter(
        (p) => p.source === 'stock' && p.status !== 'archived',
      );
    if (activeTab === 'draft') next = next.filter((p) => p.status === 'draft');
    if (activeTab === 'archived')
      next = next.filter((p) => p.status === 'archived');
    if (activeTab === 'all') next = next.filter((p) => p.status !== 'archived');

    const q = query.trim().toLowerCase();
    if (q) {
      next = next.filter(
        (p) =>
          p.title.toLowerCase().includes(q) ||
          String(p.sku).toLowerCase().includes(q),
      );
    }

    if (category !== 'all') next = next.filter((p) => p.category === category);
    if (kind !== 'all') next = next.filter((p) => p.kind === kind);
    if (brand !== 'all') next = next.filter((p) => p.brand === brand);
    if (onlyOriginal !== 'all')
      next = next.filter((p) =>
        onlyOriginal === 'yes' ? p.isOriginal : !p.isOriginal,
      );

    next.sort((a, b) => {
      if (sortBy === 'most_views' || sortBy === 'least_views') {
        const diff = (b.views ?? 0) - (a.views ?? 0);
        if (diff !== 0) return sortBy === 'most_views' ? diff : -diff;
      }

      const left = dayjs(a.addedAt).valueOf();
      const right = dayjs(b.addedAt).valueOf();
      return sortBy === 'oldest' ? left - right : right - left;
    });

    return next;
  }, [activeTab, brand, category, kind, onlyOriginal, products, query, sortBy]);

  const perPage = 5;
  const pages = Math.max(1, Math.ceil(filtered.length / perPage));
  const pageSafe = Math.min(page, pages);
  const visible = filtered.slice((pageSafe - 1) * perPage, pageSafe * perPage);

  useEffect(() => {
    setPage(1);
  }, [activeTab, query, category, kind, brand, onlyOriginal, sortBy]);

  useEffect(() => {
    setOpenMenuId(null);
  }, [activeTab, page]);

  useEffect(() => {
    setArchiveTarget(null);
  }, [activeTab, page, query, category, kind, brand, onlyOriginal, sortBy]);

  const resetAll = () => {
    setQuery('');
    setCategory('all');
    setKind('all');
    setBrand('all');
    setOnlyOriginal('all');
    setSortBy('newest');
    setPage(1);
    setSelectMode(false);
    setSelectedIds(new Set());
    setOpenMenuId(null);
  };

  const toggleSelection = (id) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

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

  const archiveProduct = (id) => {
    setProducts((prev) =>
      prev.map((p) => (p.id === id ? { ...p, status: 'archived' } : p)),
    );
    setSelectedIds((prev) => {
      const next = new Set(prev);
      next.delete(id);
      return next;
    });
    setArchiveTarget(null);
  };

  const requestArchiveProduct = (product) => {
    setArchiveTarget(product);
    setOpenMenuId(null);
  };

  const selectedCount = selectedIds.size;
  const archiveSelected = () => {
    if (!selectedCount) return;
    setProducts((prev) =>
      prev.map((p) =>
        selectedIds.has(p.id) ? { ...p, status: 'archived' } : p,
      ),
    );
    setSelectedIds(new Set());
    setSelectMode(false);
    setOpenMenuId(null);
  };

  return {
    // Data
    products,
    loading,
    filtered,
    visible,
    metrics,
    tabCounts,
    tabs,

    // Facets
    categoryFacet,
    kindFacet,
    brandFacet,
    baseForFacets,
    originalCount,
    nonOriginalCount,

    // Filter state
    activeTab,
    setActiveTab,
    query,
    setQuery,
    category,
    setCategory,
    kind,
    setKind,
    brand,
    setBrand,
    onlyOriginal,
    setOnlyOriginal,
    sortBy,
    setSortBy,

    // Pagination
    page: pageSafe,
    pages,
    setPage,
    perPage,

    // Selection
    selectMode,
    setSelectMode,
    selectedIds,
    selectedCount,
    allVisibleSelected,
    toggleSelection,
    toggleVisibleAll,

    // Archive
    archiveTarget,
    setArchiveTarget,
    archiveProduct,
    requestArchiveProduct,
    archiveSelected,

    // Menu
    openMenuId,
    setOpenMenuId,

    // Date range
    dateRange,
    setDateRange,
    hasRange,

    // Actions
    resetAll,
  };
}
