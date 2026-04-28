'use client';

import { useRef, useState } from 'react';
import { cn } from '@/lib/utils';
import ChevronIcon from '@/assets/icons/chevron.svg';
import { useOutsideClick } from '@/hooks/useOutsideClick';
import styles from './products.module.css';

function SortIcon() {
  return (
    <svg
      className={styles.sortIcon}
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden="true"
    >
      <path
        d="M5 7h14"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
      />
      <path
        d="M5 12h10"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
      />
      <path
        d="M5 17h14"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
      />
    </svg>
  );
}

export function SortControl({ value, onChange }) {
  const options = [
    { value: 'newest', label: 'Сначала новые' },
    { value: 'oldest', label: 'Сначала старые' },
    { value: 'popularity', label: 'По популярности' },
    { value: 'name_asc', label: 'По названию А → Я' },
    { value: 'name_desc', label: 'По названию Я → А' },
  ];

  const [open, setOpen] = useState(false);
  const rootRef = useRef(null);
  useOutsideClick({ open, onClose: () => setOpen(false), ref: rootRef });
  const selectedLabel =
    options.find((o) => o.value === value)?.label ?? options[0].label;

  return (
    <div className={styles.dropdownRoot} ref={rootRef}>
      <button
        type="button"
        className={cn(styles.dropdownButton, styles.sortButton)}
        onClick={() => setOpen((v) => !v)}
      >
        <SortIcon />
        <span className={styles.dropdownLabel}>{selectedLabel}</span>
        <ChevronIcon
          className={cn(styles.chevron, open && styles.chevronOpen)}
        />
      </button>

      {open && (
        <div className={styles.menu}>
          {options.map((opt) => (
            <button
              key={opt.value}
              type="button"
              onClick={() => {
                onChange(opt.value);
                setOpen(false);
              }}
              className={styles.menuItem}
            >
              <span className={styles.menuItemLabel}>{opt.label}</span>
              <span
                className={cn(
                  styles.menuCheck,
                  opt.value === value && styles.menuCheckVisible,
                )}
              >
                ✓
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
