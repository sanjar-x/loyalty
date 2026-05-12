'use client';

import { useMemo } from 'react';

import { useCategories } from '@/features/catalog/api/queries';
import { cn } from '@/lib/utils';

const ALL_TAB_ID = '__all__';
const SKELETON_WIDTHS = [58, 72, 60, 66, 80];

interface CategoryTabsProps {
  activeCategoryId: string | null;
  onCategoryChange: (categoryId: string | null) => void;
  className?: string;
}

export function CategoryTabs({
  activeCategoryId,
  onCategoryChange,
  className,
}: CategoryTabsProps) {
  const { data: categories, isLoading, isFetching } = useCategories();

  const isInitialLoading =
    (isLoading || isFetching) && !Array.isArray(categories);

  const tabs = useMemo(() => {
    if (!Array.isArray(categories)) return [];
    return categories
      .filter((c) => c && c.id != null)
      .map((c) => ({ id: c.id, name: c.name ?? '' }))
      .filter((c) => c.name.trim());
  }, [categories]);

  const activeId = activeCategoryId ?? ALL_TAB_ID;

  return (
    <div
      className={cn(
        'overflow-x-auto px-4 pb-3 pt-1 scrollbar-hide',
        className,
      )}
    >
      <div className="flex gap-1">
        {/* "Для тебя" is always visible */}
        <button
          type="button"
          onClick={() => onCategoryChange(null)}
          className={cn(
            'h-[29px] shrink-0 rounded-full px-3 text-xs font-medium whitespace-nowrap',
            'transition-colors duration-100',
            activeId === ALL_TAB_ID
              ? 'bg-[#2d2d2d] text-white'
              : 'text-[#111]',
          )}
        >
          Для тебя
        </button>

        {isInitialLoading
          ? SKELETON_WIDTHS.map((w, i) => (
              <span
                key={i}
                className="h-[29px] shrink-0 animate-pulse rounded-full bg-gray-100"
                style={{ width: `${w}px` }}
                aria-hidden
              />
            ))
          : tabs.map((tab) => (
              <button
                key={tab.id}
                type="button"
                onClick={() => onCategoryChange(tab.id)}
                className={cn(
                  'h-[29px] shrink-0 rounded-full px-3 text-xs font-medium whitespace-nowrap',
                  'transition-colors duration-100',
                  String(activeId) === String(tab.id)
                    ? 'bg-[#2d2d2d] text-white'
                    : 'text-[#111]',
                )}
              >
                {tab.name}
              </button>
            ))}
      </div>
    </div>
  );
}
