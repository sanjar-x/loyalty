'use client';

import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';
import ChevronIcon from '@/assets/icons/chevron.svg';
import { fetchCategoryTree, categoryLabel } from '@/services/categories';
import styles from './page.module.css';

function isLeaf(item) {
  return !item.children || item.children.length === 0;
}

function SkeletonColumn() {
  return (
    <div className={styles.column}>
      <div className={styles.columnList}>
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className={styles.itemSkeleton} />
        ))}
      </div>
    </div>
  );
}

function CategoryColumn({ items, selectedId, onSelect }) {
  if (!items.length) return <div className={styles.column} />;

  return (
    <div className={styles.column}>
      <div className={styles.columnList}>
        {items.map((item) => {
          const isActive = item.id === selectedId;

          if (isLeaf(item)) {
            const slug = item.fullSlug || item.slug || item.id;
            return (
              <a
                key={item.id}
                href={`/admin/products/add/details/${slug}`}
                className={styles.itemButton}
              >
                <span className={styles.itemLabel}>{categoryLabel(item)}</span>
                <ChevronIcon className={styles.itemIcon} />
              </a>
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

export default function AddProductPage() {
  const [tree, setTree] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [selectedIds, setSelectedIds] = useState([]);

  useEffect(() => {
    fetchCategoryTree()
      .then((data) => {
        const items = Array.isArray(data) ? data : [];
        setTree(items);
        // Auto-select first item at each level
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

  // Build columns dynamically based on tree depth
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

      // If items at this level are leaves, stop — no more columns needed
      if (isLeaf(currentItems[0])) break;

      currentItems = selectedItem?.children ?? [];
    }

    return result;
  }, [tree, selectedIds]);

  function handleSelect(depth, id) {
    setSelectedIds((prev) => {
      const next = prev.slice(0, depth);
      next[depth] = id;
      return next;
    });
  }

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

      {error ? (
        <p className="text-app-danger text-sm">{error}</p>
      ) : (
        <div className={styles.columns}>
          {loading
            ? Array.from({ length: 3 }).map((_, i) => (
                <SkeletonColumn key={i} />
              ))
            : columns.map((col, depth) => (
                <CategoryColumn
                  key={depth}
                  items={col.items}
                  selectedId={col.selectedId}
                  onSelect={(id) => handleSelect(depth, id)}
                />
              ))}
        </div>
      )}
    </section>
  );
}
