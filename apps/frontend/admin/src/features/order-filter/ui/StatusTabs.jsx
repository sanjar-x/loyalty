'use client';

import { ORDER_STATUS_FILTER_GROUPS } from '@/entities/order';
import { cn } from '@/shared/lib/utils';

/**
 * Status group tabs for the orders list.
 *
 * Backend doesn't yet expose per-group counts so the badge slot is hidden
 * until/unless `counts[groupKey]` arrives — we'd rather show the tab name
 * cleanly than render `… 0` everywhere.
 */
export function StatusTabs({ activeKey, counts, onChange }) {
  return (
    <div className="border-app-border flex items-end gap-6 overflow-x-auto border-b px-0.5 pb-0 md:gap-10">
      {ORDER_STATUS_FILTER_GROUPS.map(({ key, label }) => {
        const count = counts?.[key];
        const isActive = activeKey === key;
        return (
          <button
            key={key}
            type="button"
            onClick={() => onChange(key)}
            className={cn(
              'shrink-0 border-b-[3px] border-transparent pb-2.5 text-base font-medium whitespace-nowrap transition-colors',
              'text-app-muted hover:text-app-text-dark',
              isActive && 'border-app-text-dark text-app-text-dark',
            )}
          >
            {label}
            {typeof count === 'number' ? (
              <span className="text-app-muted ml-2 text-sm font-medium">
                {count}
              </span>
            ) : null}
          </button>
        );
      })}
    </div>
  );
}
