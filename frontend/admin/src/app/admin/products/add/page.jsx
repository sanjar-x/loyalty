'use client';

import Link from 'next/link';
import { useMemo, useState } from 'react';
import ChevronIcon from '@/assets/icons/chevron.svg';
// TODO: Replace with service layer import (e.g. getProductCategories from '@/services/categories') when available
import { productCategoryTree } from '@/data/productCategories';
import styles from './page.module.css';

function CategoryColumn({ items, selectedId, onSelect }) {
  if (!items.length) {
    return <div className={styles.column} />;
  }

  return (
    <div className={styles.column}>
      <div className={styles.columnList}>
        {items.map((item) => {
          const isActive = item.id === selectedId;

          return (
            <button
              key={item.id}
              type="button"
              onClick={() => onSelect(item.id)}
              className={`${styles.itemButton} ${isActive ? styles.itemButtonActive : ''}`.trim()}
            >
              <span className={styles.itemLabel}>{item.label}</span>
              <ChevronIcon className={styles.itemIcon} />
            </button>
          );
        })}
      </div>
    </div>
  );
}

export default function AddProductPage() {
  const [selectedRootId, setSelectedRootId] = useState(
    productCategoryTree[0]?.id ?? null,
  );
  const [selectedGroupId, setSelectedGroupId] = useState(
    productCategoryTree[0]?.children?.[0]?.id ?? null,
  );

  const rootItems = productCategoryTree;

  const selectedRoot = useMemo(
    () => rootItems.find((item) => item.id === selectedRootId) ?? null,
    [rootItems, selectedRootId],
  );

  const groupItems = selectedRoot?.children ?? [];

  const selectedGroup = useMemo(
    () =>
      groupItems.find((item) => item.id === selectedGroupId) ??
      groupItems[0] ??
      null,
    [groupItems, selectedGroupId],
  );

  const leafItems = selectedGroup?.children ?? [];

  const handleRootSelect = (rootId) => {
    const nextRoot = rootItems.find((item) => item.id === rootId) ?? null;
    const nextGroup = nextRoot?.children?.[0] ?? null;

    setSelectedRootId(rootId);
    setSelectedGroupId(nextGroup?.id ?? null);
  };

  const handleGroupSelect = (groupId) => {
    setSelectedGroupId(groupId);
  };

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

      <div className={styles.columns}>
        <CategoryColumn
          items={rootItems}
          selectedId={selectedRootId}
          onSelect={handleRootSelect}
        />
        <CategoryColumn
          items={groupItems}
          selectedId={selectedGroup?.id ?? null}
          onSelect={handleGroupSelect}
        />
        <div className={styles.column}>
          <div className={styles.columnList}>
            {leafItems.map((item) => (
              <Link
                key={item.id}
                href={{
                  pathname: '/admin/products/add/details',
                  query: {
                    root: selectedRoot?.id ?? '',
                    group: selectedGroup?.id ?? '',
                    leaf: item.id,
                  },
                }}
                className={styles.itemButton}
              >
                <span className={styles.itemLabel}>{item.label}</span>
                <ChevronIcon className={styles.itemIcon} />
              </Link>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
