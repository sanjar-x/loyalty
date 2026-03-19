'use client';

import { useEffect, useRef, useState } from 'react';
import ChevronIcon from '@/assets/icons/chevron.svg';
import FilterIcon from '@/assets/icons/filter.svg';
import { cn } from '@/lib/utils';

const options = [
  { value: 'newest', label: 'Сначала новые' },
  { value: 'oldest', label: 'Сначала старые' },
];

export function SortSelect({ value, onChange, variant = 'dark' }) {
  const [isOpen, setIsOpen] = useState(false);
  const rootRef = useRef(null);

  useEffect(() => {
    if (!isOpen) {
      return;
    }

    function handleClickOutside(event) {
      const target = event.target;
      if (!rootRef.current) {
        return;
      }
      if (
        typeof Node !== 'undefined' &&
        target instanceof Node &&
        rootRef.current.contains(target)
      ) {
        return;
      }
      setIsOpen(false);
    }

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isOpen]);

  const selected =
    options.find((option) => option.value === value) ?? options[0];
  const dark = variant === 'dark';

  return (
    <div className="relative w-full sm:w-[207px]" ref={rootRef}>
      <button
        type="button"
        onClick={() => setIsOpen((prev) => !prev)}
        className={cn(
          'inline-flex h-[46px] w-full items-center gap-[10px] rounded-[50px] px-[13px] py-3',
          dark ? 'bg-[#2d2d2d]' : 'bg-[#f4f3f1]',
        )}
      >
        <FilterIcon
          className={cn(
            'w-5 shrink-0',
            dark ? 'text-[#f6f6f6]' : 'text-[#1f1f1f]',
          )}
        />
        <span
          className={cn(
            'truncate text-base leading-5 font-medium',
            dark ? 'text-white' : 'text-[#111111]',
          )}
        >
          {selected.label}
        </span>
        <ChevronIcon
          className={cn(
            'ml-auto h-4 w-4 shrink-0 transition-transform',
            dark ? 'text-[#bcbcbc]' : 'text-[#8b8b8b]',
            isOpen && 'rotate-180',
          )}
        />
      </button>

      {isOpen && (
        <div className="absolute top-[calc(100%+8px)] left-0 z-30 w-[286px] overflow-hidden rounded-[18px] bg-white shadow-[0_14px_34px_rgba(22,22,22,0.16)]">
          {options.map((option, index) => {
            const isSelected = option.value === value;

            return (
              <button
                key={option.value}
                type="button"
                onClick={() => {
                  onChange(option.value);
                  setIsOpen(false);
                }}
                className={cn(
                  'flex w-full items-center justify-between px-5 py-3 text-left',
                  'text-base leading-5 font-medium text-[#111111] transition-colors hover:bg-[#f3f3f3]',
                  index > 0 && 'border-t border-[#f0f0f0]',
                )}
              >
                <span>{option.label}</span>
                <span
                  className={cn(
                    'text-2xl leading-none text-[#2d2d2d]',
                    !isSelected && 'opacity-0',
                  )}
                >
                  ✓
                </span>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
