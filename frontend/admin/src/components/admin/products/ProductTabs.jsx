'use client';

import { cn } from '@/lib/utils';
import styles from './products.module.css';

export function ProductTabs({ tabs, activeTab, tabCounts, onTabChange }) {
  return (
    <div className={styles.tabs}>
      <div className={styles.tabsInner}>
        {tabs.map((t) => {
          const active = t.key === activeTab;
          const count = tabCounts[t.key] ?? 0;
          return (
            <button
              key={t.key}
              type="button"
              onClick={() => onTabChange(t.key)}
              className={cn(
                styles.tabButton,
                active && styles.tabButtonActive,
              )}
            >
              {t.label}{' '}
              <span className={styles.tabCount}>
                {count.toLocaleString('ru-RU')}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
