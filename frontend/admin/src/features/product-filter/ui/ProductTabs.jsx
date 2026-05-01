'use client';

import { cn } from '@/shared/lib/utils';
import { productStyles as styles } from '@/entities/product';

export function ProductTabs({ tabs, activeTab, tabCounts, onTabChange }) {
  return (
    <div className={styles.tabs}>
      <div className={styles.tabsInner}>
        {tabs.map((t) => {
          const active = t.key === activeTab;
          const count = tabCounts?.[t.key];
          return (
            <button
              key={t.key}
              type="button"
              onClick={() => onTabChange(t.key)}
              className={cn(styles.tabButton, active && styles.tabButtonActive)}
            >
              {t.label}
              {count != null && (
                <>
                  {' '}
                  <span className={styles.tabCount}>
                    {count.toLocaleString('ru-RU')}
                  </span>
                </>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}
