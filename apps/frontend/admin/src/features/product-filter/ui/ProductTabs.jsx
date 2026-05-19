'use client';

import { cn } from '@/shared/lib/utils';
import { productStyles as styles } from '@/entities/product';

export function ProductTabs({ tabs, activeTab, onTabChange }) {
  return (
    <div className={styles.tabs}>
      <div className={styles.tabsInner}>
        {tabs.map((t) => {
          const active = t.key === activeTab;
          return (
            <button
              key={t.key}
              type="button"
              onClick={() => onTabChange(t.key)}
              className={cn(styles.tabButton, active && styles.tabButtonActive)}
            >
              {t.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}
