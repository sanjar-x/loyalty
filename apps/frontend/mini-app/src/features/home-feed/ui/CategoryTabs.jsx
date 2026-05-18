'use client';
import { useMemo } from 'react';

import { useGetCategoriesQuery } from '@/entities/category';
import { useDragToScroll } from '@/shared/lib/hooks';
import { cn } from '@/shared/lib/ui-utils';
import styles from './CategoryTabs.module.css';

const ALL_TAB_ID = '__all__';
const SKELETON_WIDTHS = [58, 72, 60, 66, 80];

export default function CategoryTabs({ activeCategoryId, onCategoryChange }) {
  const { data: categoriesData, isLoading, isFetching } = useGetCategoriesQuery();
  const dragRef = useDragToScroll();

  const isInitialLoading = (isLoading || isFetching) && !Array.isArray(categoriesData);

  const tabs = useMemo(() => {
    const base = [{ id: ALL_TAB_ID, name: 'Для вас' }];
    if (!Array.isArray(categoriesData)) return base;
    const cats = categoriesData
      .filter((c) => c && typeof c === 'object' && c.id != null)
      .map((c) => ({ id: c.id, name: c.name ?? c.title ?? c.label ?? '' }))
      .filter((c) => String(c.name).trim());
    return [...base, ...cats];
  }, [categoriesData]);

  const activeId = activeCategoryId ?? ALL_TAB_ID;

  return (
    <div ref={dragRef} className={cn(styles.outer, 'scrollbar-hide')}>
      <div className={styles.inner}>
        {/* "For you" always visible */}
        <button
          type="button"
          onClick={() => onCategoryChange?.(null)}
          className={cn(styles.tab, activeId === ALL_TAB_ID && styles.active)}
        >
          Для вас
        </button>

        {isInitialLoading
          ? SKELETON_WIDTHS.map((w, i) => (
              <span
                key={i}
                className={styles.skeleton}
                style={{ width: `${w}px` }}
                aria-hidden="true"
              />
            ))
          : tabs
              .filter((t) => t.id !== ALL_TAB_ID)
              .map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => onCategoryChange?.(tab.id)}
                  type="button"
                  className={cn(styles.tab, String(activeId) === String(tab.id) && styles.active)}
                >
                  {tab.name}
                </button>
              ))}
      </div>
    </div>
  );
}
