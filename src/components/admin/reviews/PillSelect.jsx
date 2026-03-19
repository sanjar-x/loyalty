'use client';

import { useEffect, useRef, useState } from 'react';
import { cn } from '@/lib/utils';
import ChevronIcon from '@/assets/icons/chevron.svg';
import { useOutsideClick } from '@/hooks/useOutsideClick';
import styles from '@/app/admin/reviews/page.module.css';

export default function PillSelect({ value, options, onChange, label, ariaLabel }) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef(null);

  useOutsideClick({ open, onClose: () => setOpen(false), ref: rootRef });

  useEffect(() => {
    if (!open) return;
    function onKey(event) {
      if (event.key === 'Escape') setOpen(false);
    }
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [open]);

  const selected = options.find((o) => o.value === value) ?? options[0];

  return (
    <div ref={rootRef} className={styles.pillRoot}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className={styles.pillButton}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-label={ariaLabel}
      >
        <span className={styles.pillLabel}>{label ?? selected.label}</span>
        {typeof selected.suffix === 'string' ? (
          <span className={styles.pillSuffix}>{selected.suffix}</span>
        ) : null}
        <span className={styles.pillChevron}>
          <ChevronIcon className={cn('h-4 w-4 transition-transform', open && 'rotate-180')} />
        </span>
      </button>

      {open && (
        <div className={styles.dropdown}>
          {options.map((opt) => {
            const isSelected = opt.value === value;
            return (
              <button
                key={opt.value}
                type="button"
                onClick={() => {
                  onChange(opt.value);
                  setOpen(false);
                }}
                className={styles.dropdownItem}
              >
                <span>{opt.label}</span>
                <span
                  className={cn(
                    styles.dropdownCheck,
                    !isSelected && styles.dropdownCheckHidden,
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
