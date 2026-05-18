'use client';
import React from 'react';
import Link from 'next/link';
import styles from './ProductInfo.module.css';
import { cn as cx } from '@/shared/lib/ui-utils';
import { getVariantThumbnail } from '@/entities/product/lib/attributes';

export default function ProductInfo({
  productName,
  brand,
  brandLink,
  // Variant selector props (new)
  variants = [],
  allMedia = [],
  selectedVariantId = null,
  onVariantChange,
  theme = 'light',
}) {
  const isDark = theme === 'dark';
  const showVariants = variants.length > 1;

  return (
    <div className={cx(styles.c1, isDark && styles.dark)}>
      {/* Brand */}
      {brandLink ? (
        <Link href={brandLink} className={cx(styles.c2, isDark && styles.brandDark)}>
          {brand}
        </Link>
      ) : (
        <h1 className={cx(styles.c2, isDark && styles.brandDark)}>{brand}</h1>
      )}

      {/* Product name */}
      {productName ? (
        <p className={cx(styles.c4, isDark && styles.nameDark)}>{productName}</p>
      ) : null}

      {/* Variants (color / model) */}
      {showVariants && (
        <div className={cx(styles.c5, 'scrollbar-hide')}>
          <div className={cx(styles.c6, styles.tw1)}>
            {variants.map((variant) => {
              const thumb = getVariantThumbnail(allMedia, variant.id);
              const label =
                variant.name ??
                (variant.nameI18N && (variant.nameI18N.ru || variant.nameI18N.en)) ??
                '';
              const isActive = variant.id === selectedVariantId;

              return (
                <button
                  key={variant.id}
                  type="button"
                  onClick={() => onVariantChange?.(variant.id)}
                  className={cx(
                    styles.thumbButton,
                    isActive ? styles.thumbActive : styles.thumbInactive
                  )}
                  style={{ width: 83, height: 83 }}
                  aria-label={label || `Вариант`}
                  aria-pressed={isActive}
                >
                  {thumb ? (
                    <img
                      src={thumb}
                      alt={label}
                      style={{
                        width: '100%',
                        height: '100%',
                        objectFit: 'cover',
                        borderRadius: 8,
                      }}
                    />
                  ) : (
                    <span
                      style={{
                        fontSize: 11,
                        lineHeight: 1.2,
                        padding: '4px 6px',
                        display: 'block',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                      }}
                    >
                      {label || '—'}
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
