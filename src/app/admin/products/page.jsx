'use client';

import Link from 'next/link';
import { cn } from '@/lib/utils';
import SearchIcon from '@/assets/icons/search.svg';
import { getProducts } from '@/services/products';
import { useProductFilters, tabs } from '@/hooks/useProductFilters';
import { Pagination } from '@/components/ui/Pagination';
import { DropdownPill } from '@/components/admin/products/DropdownPill';
import { SortControl } from '@/components/admin/products/SortControl';
import { ProductRow } from '@/components/admin/products/ProductRow';
import { ArchiveConfirmModal } from '@/components/admin/products/ArchiveConfirmModal';
import { BulkBar } from '@/components/admin/products/BulkBar';
import { ProductMetrics } from '@/components/admin/products/ProductMetrics';
import { ProductTabs } from '@/components/admin/products/ProductTabs';
import { ProductRowSkeleton } from '@/components/admin/products/ProductRowSkeleton';
import styles from './page.module.css';

export default function ProductsPage() {
  const {
    visible,
    loading,
    metrics,
    tabCounts,
    categoryFacet,
    kindFacet,
    brandFacet,
    baseForFacets,
    originalCount,
    nonOriginalCount,
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
    page,
    pages,
    setPage,
    selectMode,
    setSelectMode,
    selectedIds,
    selectedCount,
    allVisibleSelected,
    toggleSelection,
    toggleVisibleAll,
    archiveTarget,
    setArchiveTarget,
    archiveProduct,
    requestArchiveProduct,
    archiveSelected,
    openMenuId,
    setOpenMenuId,
    dateRange,
    setDateRange,
    hasRange,
    resetAll,
  } = useProductFilters(() => getProducts());

  return (
    <section className={styles.page}>
      <div className={styles.header}>
        <h1 className={styles.title}>Товары</h1>
        <Link href="/admin/products/add" className={styles.primaryButton}>
          Добавить товар
        </Link>
      </div>

      <div className={styles.card} style={{ marginTop: 16 }}>
        <p className={styles.cardLabel}>Просмотры</p>
        <ProductMetrics
          metrics={metrics}
          dateRange={dateRange}
          hasRange={hasRange}
          onDateRangeChange={setDateRange}
        />
      </div>

      <ProductTabs
        tabs={tabs}
        activeTab={activeTab}
        tabCounts={tabCounts}
        onTabChange={setActiveTab}
      />

      <div className={styles.filters}>
        <button
          type="button"
          onClick={() => {
            if (!selectMode) {
              setSelectMode(true);
              return;
            }
            toggleVisibleAll();
          }}
          className={styles.pillButton}
        >
          <span
            className={cn(
              styles.check,
              selectMode && allVisibleSelected && styles.checkChecked,
            )}
          >
            <svg
              width="12"
              height="10"
              viewBox="0 0 14 12"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
            >
              <path
                d="M0.707031 5.14014L5.20703 9.64014L12.707 0.640137"
                stroke="white"
                strokeWidth="1.8"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </span>
          Выбрать товары
        </button>

        <div className={styles.search}>
          <SearchIcon className={styles.searchIcon} />
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Поиск по товарам"
            className={styles.searchInput}
          />
        </div>

        <div className={styles.selectWrap}>
          <DropdownPill
            label="Категория"
            value={category}
            displayValue={
              category === 'all'
                ? ''
                : `${category} ${(categoryFacet.counts.get(category) ?? 0).toLocaleString('ru-RU')}`
            }
            active={category !== 'all'}
            options={categoryFacet.options.map((opt) => ({
              ...opt,
              label: opt.value === 'all' ? 'Все категории' : opt.label,
            }))}
            onChange={setCategory}
          />
        </div>
        <div className={styles.selectWrap}>
          <DropdownPill
            label="Тип"
            value={kind}
            displayValue={
              kind === 'all'
                ? ''
                : `${kind} ${(kindFacet.counts.get(kind) ?? 0).toLocaleString('ru-RU')}`
            }
            active={kind !== 'all'}
            options={kindFacet.options.map((opt) => ({
              ...opt,
              label: opt.value === 'all' ? 'Все типы' : opt.label,
            }))}
            onChange={setKind}
          />
        </div>
        <div className={styles.selectWrap}>
          <DropdownPill
            label="Бренд"
            value={brand}
            displayValue={
              brand === 'all'
                ? ''
                : `${brand} ${(brandFacet.counts.get(brand) ?? 0).toLocaleString('ru-RU')}`
            }
            active={brand !== 'all'}
            options={brandFacet.options.map((opt) => ({
              ...opt,
              label: opt.value === 'all' ? 'Все бренды' : opt.label,
              searchable: true,
              groupByInitial: true,
            }))}
            onChange={setBrand}
          />
        </div>

        <div className={styles.selectWrap}>
          <DropdownPill
            label="Оригинал"
            value={onlyOriginal}
            displayValue={
              onlyOriginal === 'all'
                ? originalCount.toLocaleString('ru-RU')
                : onlyOriginal === 'yes'
                  ? `Да · ${originalCount.toLocaleString('ru-RU')}`
                  : `Нет · ${nonOriginalCount.toLocaleString('ru-RU')}`
            }
            active={onlyOriginal !== 'all'}
            options={[
              {
                value: 'all',
                label: 'Все',
                count: baseForFacets.length,
              },
              {
                value: 'yes',
                label: 'Оригинал',
                count: originalCount,
              },
              {
                value: 'no',
                label: 'Не оригинал',
                count: nonOriginalCount,
              },
            ]}
            onChange={setOnlyOriginal}
          />
        </div>

        <div className={styles.selectWrap}>
          <SortControl value={sortBy} onChange={setSortBy} />
        </div>

        <button
          type="button"
          onClick={resetAll}
          className={styles.filtersReset}
          aria-label="Сбросить фильтры"
        >
          <svg
            width="15"
            height="15"
            viewBox="0 0 15 15"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path
              d="M1 1L7.5 7.5M14 14L7.5 7.5M7.5 7.5L13.5357 1M7.5 7.5L1 14"
              stroke="#2D2D2D"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </button>
      </div>

      <div className={styles.table}>
        {loading ? (
          <div className={styles.loadingList}>
            <ProductRowSkeleton />
            <ProductRowSkeleton />
            <ProductRowSkeleton />
          </div>
        ) : (
          <div className={styles.rows}>
            {visible.map((p) => (
              <ProductRow
                key={p.id}
                product={p}
                checked={selectedIds.has(p.id)}
                selectMode={selectMode}
                openMenuId={openMenuId}
                onToggleSelection={(id) => {
                  if (!selectMode) setSelectMode(true);
                  toggleSelection(id);
                }}
                onSetOpenMenuId={setOpenMenuId}
                onRequestArchive={requestArchiveProduct}
              />
            ))}
          </div>
        )}
      </div>

      <Pagination page={page} pages={pages} onPage={setPage} />

      {selectMode && selectedCount > 0 && (
        <BulkBar
          selectedCount={selectedCount}
          onArchive={archiveSelected}
        />
      )}

      <ArchiveConfirmModal
        product={archiveTarget}
        onClose={() => setArchiveTarget(null)}
        onConfirm={archiveProduct}
      />
    </section>
  );
}
