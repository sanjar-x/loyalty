'use client';

import { useMemo } from 'react';
import styles from './styles/productForm.module.css';

/**
 * Horizontal variant tab strip.
 *
 * Each variant is shown as a thumbnail square. The active tab has a
 * selected border. A "+" button appends a new variant.
 *
 * Props:
 *   variants:          Array<{ localId, images }> — per-variant state slices
 *   activeIndex:       number — currently selected variant tab
 *   onSwitch:          (index) => void
 *   onAdd:             () => void
 *   onRemove:          (index) => void
 *   uploads:           object — imageUpload.uploads map for resolving blob URLs
 *   errorIndices:      Set<number> | null — variant indices with validation errors
 */
export default function VariantTabs({
  variants = [],
  activeIndex = 0,
  onSwitch,
  onAdd,
  onRemove,
  uploads = {},
  errorIndices = null,
}) {
  // Derive thumbnail URL per variant (first image or null)
  const thumbnails = useMemo(
    () =>
      variants.map((v) => {
        const first = v.images?.[0];
        if (!first) return null;
        return uploads[first.localId]?.url || first.url || null;
      }),
    [variants, uploads],
  );

  return (
    <div className={styles.variantTabStrip}>
      {variants.map((variant, idx) => {
        const isActive = idx === activeIndex;
        const thumb = thumbnails[idx];
        const hasError = errorIndices?.has(idx);

        return (
          <div
            key={variant.localId}
            className={`${
              isActive ? styles.variantTabActive : styles.variantTab
            }${hasError ? ` ${styles.variantTabError}` : ''}`}
            onClick={() => onSwitch(idx)}
            onKeyDown={(e) =>
              (e.key === 'Enter' || e.key === ' ') && onSwitch(idx)
            }
            aria-label={`Вариант ${idx + 1}${hasError ? ' (есть ошибки)' : ''}`}
            aria-selected={isActive}
            role="tab"
            tabIndex={0}
          >
            {thumb ? (
              <img
                src={thumb}
                alt=""
                className={styles.variantTabImage}
                draggable={false}
              />
            ) : (
              <div className={styles.variantTabPlaceholder}>
                <svg
                  width="24"
                  height="24"
                  viewBox="0 0 24 24"
                  fill="none"
                  xmlns="http://www.w3.org/2000/svg"
                  aria-hidden="true"
                >
                  <rect
                    x="3"
                    y="3"
                    width="18"
                    height="18"
                    rx="3"
                    stroke="#C4C4C4"
                    strokeWidth="1.5"
                    strokeDasharray="4 3"
                  />
                  <path
                    d="M8 16L10.59 12.51C10.79 12.24 11.19 12.24 11.39 12.51L13 14.69L15.59 11.01C15.79 10.74 16.19 10.74 16.39 11.01L18 13.5"
                    stroke="#C4C4C4"
                    strokeWidth="1.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                  <circle cx="9.5" cy="8.5" r="1.5" fill="#C4C4C4" />
                </svg>
              </div>
            )}
            {hasError && <span className={styles.variantTabErrorDot} />}
            {idx > 0 && (
              <button
                type="button"
                className={styles.variantTabRemove}
                onClick={(e) => {
                  e.stopPropagation();
                  onRemove?.(idx);
                }}
                aria-label={`Удалить вариант ${idx + 1}`}
              >
                ×
              </button>
            )}
          </div>
        );
      })}

      <button
        type="button"
        className={styles.variantTabAdd}
        onClick={onAdd}
        aria-label="Добавить вариант"
      >
        <svg
          width="24"
          height="24"
          viewBox="0 0 24 24"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          aria-hidden="true"
        >
          <path
            d="M12 5V19M5 12H19"
            stroke="#111111"
            strokeWidth="2"
            strokeLinecap="round"
          />
        </svg>
      </button>
    </div>
  );
}
