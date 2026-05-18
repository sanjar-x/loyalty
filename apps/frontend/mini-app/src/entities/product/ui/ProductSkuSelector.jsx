'use client';
import React from 'react';
import { cn as cx } from '@/shared/lib/ui-utils';
import styles from './ProductSizes.module.css';

/**
 * Generic SKU/variant selector.
 * Renders one row of pill buttons per SKU.
 * Each option: { id, label, sublabel?, isAvailable, price? }.
 * Used on PDP when attribute labels (sizes/colors) cannot be resolved yet —
 * falls back to SKU-code / index labels so users can still pick a concrete SKU.
 */
export default function ProductSkuSelector({
  options = [],
  selectedId,
  onSelect,
  title = 'Вариант',
  theme = 'light',
}) {
  const isDark = theme === 'dark';

  if (!Array.isArray(options) || options.length === 0) return null;

  return (
    <div className={cx(styles.c1, isDark && styles.dark)}>
      <div className={cx(styles.c2, styles.tw1)}>
        <div className={cx(styles.c3, styles.tw2)}>
          <h3 className={styles.c4}>{title}</h3>
        </div>

        <div className={cx(styles.c5, styles.tw3, isDark && styles.sizesRowDark)}>
          {options.map((opt) => {
            const isSelected = String(selectedId) === String(opt.id);
            const isAvailable = opt.isAvailable !== false;
            return (
              <button
                key={opt.id}
                type="button"
                onClick={() => isAvailable && onSelect?.(opt)}
                disabled={!isAvailable}
                className={cx(
                  styles.sizeButton,
                  isDark && styles.sizeButtonDark,
                  !isAvailable
                    ? styles.sizeDisabled
                    : isSelected
                      ? styles.sizeSelected
                      : styles.sizeDefault
                )}
                style={{ fontFamily: 'Inter' }}
                aria-pressed={isSelected}
                title={opt.sublabel || opt.label}
              >
                {opt.label}
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
