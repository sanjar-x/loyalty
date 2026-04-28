'use client';

import Link from 'next/link';
import { cn, pluralizeRu } from '@/lib/utils';
import SearchIcon from '@/assets/icons/search.svg';
import CloseIcon from '@/assets/icons/close.svg';
import { useProductFilters, tabs } from '@/hooks/useProductFilters';
import { Pagination } from '@/components/ui/Pagination';
import { SortControl } from '@/components/admin/products/SortControl';
import { ProductRow } from '@/components/admin/products/ProductRow';
import { ArchiveConfirmModal } from '@/components/admin/products/ArchiveConfirmModal';
import { DeleteConfirmModal } from '@/components/admin/products/DeleteConfirmModal';
import { BulkBar } from '@/components/admin/products/BulkBar';
import { ProductTabs } from '@/components/admin/products/ProductTabs';
import { ProductRowSkeleton } from '@/components/admin/products/ProductRowSkeleton';
import { DropdownPill } from '@/components/admin/products/DropdownPill';
import styles from './page.module.css';

const PER_PAGE_OPTIONS = [10, 25, 50];

function ActiveFilters({ query, setQuery, brandFilter, setBrandFilter, brandOptions }) {
  const chips = [];

  if (query.trim())
    chips.push({ label: `«${query.trim()}»`, onRemove: () => setQuery('') });

  if (brandFilter !== 'all') {
    const brand = brandOptions.find((o) => o.value === brandFilter);
    chips.push({
      label: `Бренд: ${brand?.label ?? brandFilter}`,
      onRemove: () => setBrandFilter('all'),
    });
  }

  if (!chips.length) return null;

  return (
    <div className={styles.activeFilters}>
      {chips.map((chip) => (
        <span key={chip.label} className={styles.filterChip}>
          {chip.label}
          <button
            type="button"
            className={styles.filterChipRemove}
            onClick={chip.onRemove}
            aria-label={`Убрать фильтр ${chip.label}`}
          >
            <CloseIcon className={styles.filterChipIcon} />
          </button>
        </span>
      ))}
    </div>
  );
}

function ResultsInfo({ page, perPage, total, searchActive, searchCount }) {
  if (total === 0 && !searchActive) return null;

  if (searchActive) {
    const label = pluralizeRu(searchCount, 'совпадение', 'совпадения', 'совпадений');
    return (
      <p className={styles.resultsInfo}>
        {searchCount} {label} на странице
      </p>
    );
  }

  const from = (page - 1) * perPage + 1;
  const to = Math.min(page * perPage, total);
  const label = pluralizeRu(total, 'товар', 'товара', 'товаров');

  return (
    <p className={styles.resultsInfo}>
      {from}–{to} из {total.toLocaleString('ru-RU')} {label}
    </p>
  );
}

function StatusError({ message }) {
  if (!message) return null;
  return (
    <div className={styles.statusError} role="alert">
      <span className={styles.statusErrorIcon}>⚠</span>
      {message}
    </div>
  );
}

function EmptyResults({ hasFilters, onReset }) {
  return (
    <div className={styles.emptyState}>
      <p className={styles.emptyTitle}>Ничего не найдено</p>
      <p className={styles.emptyText}>
        {hasFilters
          ? 'Попробуйте изменить фильтры или сбросить их.'
          : 'Товары пока не добавлены.'}
      </p>
      {hasFilters && (
        <button
          type="button"
          className={styles.emptyResetButton}
          onClick={onReset}
        >
          Сбросить фильтры
        </button>
      )}
    </div>
  );
}

function ErrorState({ message, onRetry }) {
  return (
    <div className={styles.emptyState}>
      <p className={styles.emptyTitle}>Ошибка загрузки</p>
      <p className={styles.emptyText}>{message}</p>
      <button
        type="button"
        className={styles.emptyResetButton}
        onClick={onRetry}
      >
        Повторить
      </button>
    </div>
  );
}

function PerPageSelector({ value, onChange }) {
  return (
    <div className={styles.perPageWrap}>
      <span className={styles.perPageLabel}>Показывать по</span>
      <div className={styles.perPageButtons}>
        {PER_PAGE_OPTIONS.map((n) => (
          <button
            key={n}
            type="button"
            className={cn(
              styles.perPageButton,
              n === value && styles.perPageButtonActive,
            )}
            onClick={() => onChange(n)}
          >
            {n}
          </button>
        ))}
      </div>
    </div>
  );
}

export default function ProductsPage() {
  const {
    visible,
    loading,
    error,
    statusError,
    total,
    tabCounts,
    activeTab,
    setActiveTab,
    query,
    setQuery,
    searchActive,
    sortBy,
    setSortBy,
    brandFilter,
    setBrandFilter,
    brandOptions,
    page,
    pages,
    setPage,
    perPage,
    setPerPage,
    totalFiltered,
    selectedIds,
    selectedCount,
    allVisibleSelected,
    toggleSelection,
    toggleVisibleAll,
    clearSelection,
    archiveTarget,
    setArchiveTarget,
    archiveProduct,
    requestArchiveProduct,
    archiveSelected,
    deleteTarget,
    setDeleteTarget,
    confirmDeleteProduct,
    requestDeleteProduct,
    deleteSelected,
    updateProductStatus,
    hasActiveFilters,
    openMenuId,
    setOpenMenuId,
    resetAll,
    retry,
  } = useProductFilters();

  return (
    <section className={styles.page}>
      <div className={styles.header}>
        <h1 className={styles.title}>Товары</h1>
        <Link href="/admin/products/add" className={styles.primaryButton}>
          Добавить товар
        </Link>
      </div>

      <StatusError message={statusError} />

      <ProductTabs
        tabs={tabs}
        activeTab={activeTab}
        tabCounts={tabCounts}
        onTabChange={setActiveTab}
      />

      <div className={styles.filters}>
        <button
          type="button"
          onClick={toggleVisibleAll}
          className={styles.pillButton}
        >
          <span
            className={cn(
              styles.check,
              allVisibleSelected && selectedCount > 0 && styles.checkChecked,
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
          Выбрать все
        </button>

        <div className={styles.search}>
          <SearchIcon className={styles.searchIcon} />
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Найти на странице"
            className={styles.searchInput}
          />
          {query && (
            <button
              type="button"
              className={styles.searchClear}
              onClick={() => setQuery('')}
              aria-label="Очистить поиск"
            >
              <CloseIcon className={styles.searchClearIcon} />
            </button>
          )}
        </div>

        {brandOptions.length > 1 && (
          <div className={styles.filterItem}>
            <DropdownPill
              label="Бренд"
              value={brandFilter}
              options={brandOptions}
              onChange={setBrandFilter}
            />
          </div>
        )}

        <div className={styles.selectWrap}>
          <SortControl value={sortBy} onChange={setSortBy} />
        </div>

        {hasActiveFilters && (
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
        )}
      </div>

      <ActiveFilters
        query={query}
        setQuery={setQuery}
        brandFilter={brandFilter}
        setBrandFilter={setBrandFilter}
        brandOptions={brandOptions}
      />

      {/* Product list */}
      <div className={styles.table}>
        {error ? (
          <ErrorState message={error} onRetry={retry} />
        ) : loading ? (
          <div className={styles.loadingList}>
            <ProductRowSkeleton />
            <ProductRowSkeleton />
            <ProductRowSkeleton />
          </div>
        ) : visible.length === 0 ? (
          <EmptyResults
            hasFilters={hasActiveFilters || query.trim() !== ''}
            onReset={resetAll}
          />
        ) : (
          <div className={styles.rows}>
            {visible.map((p) => (
              <ProductRow
                key={p.id}
                product={p}
                checked={selectedIds.has(p.id)}
                openMenuId={openMenuId}
                onToggleSelection={toggleSelection}
                onSetOpenMenuId={setOpenMenuId}
                onStatusChange={updateProductStatus}
                onRequestArchive={requestArchiveProduct}
                onRequestDelete={requestDeleteProduct}
              />
            ))}
          </div>
        )}
      </div>

      {/* Pagination footer */}
      {!loading && !error && totalFiltered > 0 && (
        <div className={styles.paginationFooter}>
          <ResultsInfo
            page={page}
            perPage={perPage}
            total={totalFiltered}
            searchActive={searchActive}
            searchCount={visible.length}
          />
          <Pagination page={page} pages={pages} onPage={setPage} />
          <PerPageSelector value={perPage} onChange={setPerPage} />
        </div>
      )}

      {selectedCount > 0 && (
        <BulkBar
          selectedCount={selectedCount}
          onArchive={archiveSelected}
          onDelete={deleteSelected}
          onClear={clearSelection}
        />
      )}

      <ArchiveConfirmModal
        product={archiveTarget}
        onClose={() => setArchiveTarget(null)}
        onConfirm={archiveProduct}
      />

      <DeleteConfirmModal
        product={deleteTarget}
        onClose={() => setDeleteTarget(null)}
        onConfirm={confirmDeleteProduct}
      />
    </section>
  );
}
