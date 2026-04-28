'use client';

import Link from 'next/link';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import ChevronIcon from '@/assets/icons/chevron.svg';
import SearchIcon from '@/assets/icons/search.svg';
import CloseIcon from '@/assets/icons/close.svg';
import { fetchCategoryTree, categoryLabel } from '@/services/categories';
import styles from './page.module.css';

const COLUMN_LABELS = ['Раздел', 'Категория', 'Тип товара'];
const RECENT_KEY = 'loyality:recent-categories';
const MAX_RECENT = 5;

function isLeaf(item) {
  return !item.children || item.children.length === 0;
}

// Flatten tree into searchable list of leaf paths
function flattenTree(nodes, path = []) {
  const results = [];
  for (const node of nodes) {
    const label = categoryLabel(node);
    const currentPath = [...path, { id: node.id, label, node }];
    if (isLeaf(node)) {
      results.push({
        id: node.id,
        slug: node.fullSlug || node.slug || node.id,
        labels: currentPath.map((p) => p.label),
        searchText: currentPath.map((p) => p.label.toLowerCase()).join(' '),
        path: currentPath,
      });
    } else if (node.children?.length) {
      results.push(...flattenTree(node.children, currentPath));
    }
  }
  return results;
}

// Read recent categories from localStorage
function getRecent() {
  try {
    const raw = localStorage.getItem(RECENT_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

// Save a category selection to recents
function saveRecent(entry) {
  try {
    const prev = getRecent().filter((r) => r.slug !== entry.slug);
    const next = [entry, ...prev].slice(0, MAX_RECENT);
    localStorage.setItem(RECENT_KEY, JSON.stringify(next));
  } catch {
    /* storage full — ignore */
  }
}

function SkeletonColumn({ count = 6 }) {
  return (
    <div className={styles.column}>
      <div className={styles.columnHeader}>
        <div className={styles.columnHeaderSkeleton} />
      </div>
      <div className={styles.columnList}>
        {Array.from({ length: count }).map((_, i) => (
          <div key={i} className={styles.itemSkeleton} />
        ))}
      </div>
    </div>
  );
}

function CategoryColumn({ items, selectedId, onSelect, label }) {
  if (!items.length) return null;

  return (
    <div className={styles.column}>
      {label && <div className={styles.columnHeader}>{label}</div>}
      <div className={styles.columnList}>
        {items.map((item) => {
          const isActive = item.id === selectedId;

          if (isLeaf(item)) {
            const slug = item.fullSlug || item.slug || item.id;
            return (
              <Link
                key={item.id}
                href={`/admin/products/add/details/${slug}`}
                className={styles.itemButton}
                onClick={() =>
                  saveRecent({
                    slug,
                    label: categoryLabel(item),
                  })
                }
              >
                <span className={styles.itemLabel}>
                  {categoryLabel(item)}
                </span>
                <ChevronIcon className={styles.itemIcon} />
              </Link>
            );
          }

          return (
            <button
              key={item.id}
              type="button"
              onClick={() => onSelect(item.id)}
              className={`${styles.itemButton} ${isActive ? styles.itemButtonActive : ''}`.trim()}
            >
              <span className={styles.itemLabel}>{categoryLabel(item)}</span>
              <ChevronIcon className={styles.itemIcon} />
            </button>
          );
        })}
      </div>
    </div>
  );
}

function SearchResults({ query, flatItems }) {
  const q = query.toLowerCase().trim();
  const results = useMemo(
    () => flatItems.filter((item) => item.searchText.includes(q)),
    [flatItems, q],
  );

  if (!results.length) {
    return (
      <div className={styles.searchEmpty}>
        <p className={styles.searchEmptyText}>
          Ничего не найдено по запросу «{query}»
        </p>
      </div>
    );
  }

  return (
    <div className={styles.searchResults}>
      {results.map((item) => (
        <Link
          key={item.slug}
          href={`/admin/products/add/details/${item.slug}`}
          className={styles.searchResultItem}
          onClick={() =>
            saveRecent({
              slug: item.slug,
              label: item.labels[item.labels.length - 1],
            })
          }
        >
          <span className={styles.searchResultLabel}>
            {item.labels[item.labels.length - 1]}
          </span>
          <span className={styles.searchResultPath}>
            {item.labels.slice(0, -1).join(' → ')}
          </span>
        </Link>
      ))}
    </div>
  );
}

function RecentCategories() {
  const [recent, setRecent] = useState([]);

  useEffect(() => {
    setRecent(getRecent());
  }, []);

  if (!recent.length) return null;

  return (
    <div className={styles.recentSection}>
      <div className={styles.recentHeader}>Недавние</div>
      <div className={styles.recentList}>
        {recent.map((r) => (
          <Link
            key={r.slug}
            href={`/admin/products/add/details/${r.slug}`}
            className={styles.recentChip}
          >
            {r.label}
          </Link>
        ))}
      </div>
    </div>
  );
}

export default function AddProductPage() {
  const [tree, setTree] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [selectedIds, setSelectedIds] = useState([]);
  const [search, setSearch] = useState('');
  const searchRef = useRef(null);

  const loadTree = useCallback(() => {
    setLoading(true);
    setError('');
    fetchCategoryTree()
      .then((data) => {
        const items = Array.isArray(data) ? data : [];
        setTree(items);
        const ids = [];
        let current = items;
        while (current?.length) {
          ids.push(current[0].id);
          current = current[0].children;
        }
        setSelectedIds(ids);
      })
      .catch(() => setError('Не удалось загрузить категории'))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    loadTree();
  }, [loadTree]);

  const flatItems = useMemo(() => flattenTree(tree), [tree]);

  const columns = useMemo(() => {
    const result = [];
    let currentItems = tree;

    for (let depth = 0; currentItems?.length; depth++) {
      const selectedId = selectedIds[depth] ?? null;
      const selectedItem =
        currentItems.find((item) => item.id === selectedId) ??
        currentItems[0] ??
        null;

      result.push({
        items: currentItems,
        selectedId: selectedItem?.id ?? null,
      });

      if (isLeaf(currentItems[0])) break;
      currentItems = selectedItem?.children ?? [];
    }

    return result;
  }, [tree, selectedIds]);

  // Breadcrumb path from selected items
  const breadcrumb = useMemo(() => {
    const parts = [];
    let currentItems = tree;
    for (const id of selectedIds) {
      const found = currentItems.find((item) => item.id === id);
      if (!found) break;
      parts.push(categoryLabel(found));
      currentItems = found.children ?? [];
    }
    return parts;
  }, [tree, selectedIds]);

  function handleSelect(depth, id) {
    setSelectedIds((prev) => {
      const next = prev.slice(0, depth);
      next[depth] = id;
      return next;
    });
  }

  const isSearching = search.trim().length > 0;

  return (
    <section className={styles.page}>
      <div className={styles.header}>
        <Link
          href="/admin/products"
          className={styles.backButton}
          aria-label="Назад к товарам"
        >
          <ChevronIcon className={styles.backIcon} />
        </Link>
        <h1 className={styles.title}>Добавление товара</h1>
      </div>

      {/* Search bar */}
      <div className={styles.searchBar}>
        <SearchIcon className={styles.searchIcon} />
        <input
          ref={searchRef}
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Поиск категории..."
          className={styles.searchInput}
        />
        {search && (
          <button
            type="button"
            className={styles.searchClear}
            onClick={() => {
              setSearch('');
              searchRef.current?.focus();
            }}
            aria-label="Очистить поиск"
          >
            <CloseIcon className={styles.searchClearIcon} />
          </button>
        )}
      </div>

      {error ? (
        <div className={styles.errorState}>
          <p className={styles.errorText}>Не удалось загрузить категории</p>
          <button
            type="button"
            className={styles.retryButton}
            onClick={loadTree}
          >
            Попробовать снова
          </button>
        </div>
      ) : isSearching ? (
        <SearchResults query={search} flatItems={flatItems} />
      ) : (
        <>
          <RecentCategories />

          {!loading && tree.length === 0 ? (
            <div className={styles.emptyState}>
              <p className={styles.emptyText}>
                Категории пока не созданы. Обратитесь к администратору.
              </p>
            </div>
          ) : (
            <div className={styles.columns}>
              {loading
                ? [3, 10].map((count, i) => (
                    <SkeletonColumn key={i} count={count} />
                  ))
                : columns.map((col, depth) => (
                    <CategoryColumn
                      key={depth}
                      items={col.items}
                      selectedId={col.selectedId}
                      onSelect={(id) => handleSelect(depth, id)}
                      label={COLUMN_LABELS[depth] ?? `Уровень ${depth + 1}`}
                    />
                  ))}
            </div>
          )}

          {/* Breadcrumb path */}
          {!loading && breadcrumb.length > 1 && (
            <div className={styles.summary}>
              <span className={styles.summaryLabel}>Выбрано:</span>
              {breadcrumb.join(' → ')}
            </div>
          )}
        </>
      )}
    </section>
  );
}
